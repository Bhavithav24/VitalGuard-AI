import assert from 'node:assert/strict';

const baseUrl = (process.env.VITALGUARD_API_URL || 'https://vitalguard-risk-api.onrender.com').replace(/\/$/, '');
const timeoutMs = 20_000;

async function request(path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    signal: AbortSignal.timeout(timeoutMs),
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers || {}),
    },
  });
  const body = await response.text();
  let data;
  try {
    data = body ? JSON.parse(body) : null;
  } catch {
    data = body;
  }
  assert.ok(response.ok, `${options.method || 'GET'} ${path} returned ${response.status}: ${body}`);
  return { response, data };
}

async function main() {
  console.log(`Smoke-testing VitalGuard API: ${baseUrl}`);

  const { data: health } = await request('/health');
  assert.equal(health.status, 'ok');
  assert.equal(health.demo_only, true);
  console.log('✓ Health endpoint');

  const { data: model } = await request('/api/v1/model/info');
  assert.equal(model.demo_only, true);
  assert.equal(model.clinically_validated, false);
  assert.ok(Array.isArray(model.features) && model.features.length >= 7);
  console.log('✓ Model metadata and demo disclaimer');

  const preflight = await fetch(`${baseUrl}/api/v1/risk/predict`, {
    method: 'OPTIONS',
    headers: {
      Origin: 'https://vitalguard-ai-g215.onrender.com',
      'Access-Control-Request-Method': 'POST',
      'Access-Control-Request-Headers': 'content-type',
    },
    signal: AbortSignal.timeout(timeoutMs),
  });
  assert.ok(preflight.ok, `CORS preflight returned ${preflight.status}`);
  assert.equal(
    preflight.headers.get('access-control-allow-origin'),
    'https://vitalguard-ai-g215.onrender.com',
    'CORS must allow the deployed frontend origin',
  );
  console.log('✓ Frontend CORS preflight');

  // Use fictional observations and a unique demo identifier so this test never
  // touches a real patient record. The API intentionally persists demo outputs.
  const patientId = `SMOKE-${Date.now()}`;
  const { data: prediction } = await request('/api/v1/risk/predict', {
    method: 'POST',
    body: JSON.stringify({
      patient_id: patientId,
      age: 58,
      heart_rate: 82,
      spo2: 98,
      systolic_bp: 122,
      diastolic_bp: 78,
      temperature: 37,
      respiratory_rate: 16,
    }),
  });
  assert.equal(prediction.patient_id, patientId);
  assert.equal(prediction.demo_only, true);
  assert.ok(Number.isInteger(prediction.risk_score) && prediction.risk_score >= 0 && prediction.risk_score <= 100);
  assert.ok(['low', 'moderate', 'high', 'critical'].includes(prediction.risk_level));
  assert.ok(prediction.observation_id > 0);
  assert.ok(prediction.created_at);
  console.log('✓ Prediction response and validation');

  const historyPath = `/api/v1/observations?patient_id=${encodeURIComponent(patientId)}&limit=10`;
  const { data: history } = await request(historyPath);
  assert.equal(history.demo_only, true);
  assert.equal(history.count, 1);
  assert.equal(history.items[0].id, prediction.observation_id);
  assert.equal(history.items[0].patient_id, patientId);
  assert.equal(history.items[0].inputs.spo2, 98);
  console.log('✓ Prediction persisted and returned by history');

  const invalid = await fetch(`${baseUrl}/api/v1/risk/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      patient_id: patientId,
      age: 58,
      heart_rate: 82,
      spo2: 140,
      systolic_bp: 122,
      diastolic_bp: 78,
      temperature: 37,
      respiratory_rate: 16,
    }),
    signal: AbortSignal.timeout(timeoutMs),
  });
  assert.equal(invalid.status, 422, 'Out-of-range vitals should be rejected with 422');
  console.log('✓ Invalid input rejected');

  console.log('All live API smoke checks passed. Synthetic demo data only; not for clinical use.');
}

main().catch((error) => {
  console.error('VitalGuard API smoke test failed:', error);
  process.exitCode = 1;
});
