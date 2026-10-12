import {describe,it,expect,vi} from 'vitest';
import {render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {SimulationProvider} from '../store/SimulationContext.tsx';
import {DashboardPage} from '../pages/DashboardPage.tsx';
import {AlertsPage} from '../pages/AlertsPage.tsx';
import {AnalyticsPage} from '../pages/AnalyticsPage.tsx';
import {SettingsPage} from '../pages/SettingsPage.tsx';
import {PatientsPage} from '../pages/PatientsPage.tsx';
import {NotFoundPage} from '../pages/NotFoundPage.tsx';
import {formatTimeAgo} from '../utils/format.ts';
import {RISK_STYLES,CHART_COLORS} from '../theme/tokens.ts';
vi.mock('../services/api.ts',()=>({api:{
 listPatients:vi.fn().mockResolvedValue([]),
 listObservations:vi.fn().mockResolvedValue({items:[],count:0}),
 listAlerts:vi.fn().mockResolvedValue({items:[],count:0}),
 health:vi.fn().mockResolvedValue({status:'ok'}),
 acknowledgeAlert:vi.fn().mockResolvedValue({}),
 assignAlert:vi.fn().mockResolvedValue({}),
 resolveAlert:vi.fn().mockResolvedValue({}),
 createPatient:vi.fn(),updatePatient:vi.fn(),deactivatePatient:vi.fn(),
}}));
vi.mock('../services/useLiveEvents.ts',()=>({useLiveEvents:()=>({status:'disconnected',eventCount:0})}));
function wrap(ui:React.ReactNode){return render(<SimulationProvider><MemoryRouter>{ui}</MemoryRouter></SimulationProvider>)}
describe('backend-authoritative routes render',()=>{
 it('dashboard renders without local patient fixtures',()=>{wrap(<DashboardPage/>);expect(screen.getByText('Patient Monitoring Overview')).toBeTruthy();expect(screen.getByText(/No patient data/i)).toBeTruthy()});
 it('patient directory renders an empty backend state',()=>{wrap(<PatientsPage/>);expect(screen.getByText('Patients')).toBeTruthy();expect(screen.getByText('No patients found')).toBeTruthy()});
 it('alerts render an empty backend state',()=>{wrap(<AlertsPage/>);expect(screen.getByText('Alert Center')).toBeTruthy();expect(screen.getByText('No alerts in this filter')).toBeTruthy()});
 it('analytics renders',()=>{wrap(<AnalyticsPage/>);expect(screen.getAllByText('Analytics').length).toBeGreaterThan(0);expect(screen.getByText('No persisted risk assessments yet.')).toBeTruthy()});
 it('settings renders without an auth provider in isolated tests',()=>{wrap(<SettingsPage/>);expect(screen.getAllByRole('heading',{name:'Settings'}).length).toBeGreaterThan(0)});
 it('unknown route works',()=>{wrap(<NotFoundPage/>);expect(screen.getAllByText('404').length).toBeGreaterThan(0)});
 it('formatting helpers + centralized tokens',()=>{expect(formatTimeAgo(new Date().toISOString())).toBe('Just now');expect(formatTimeAgo(new Date(Date.now()-120000).toISOString())).toBe('2 min ago');expect(RISK_STYLES.high).toBeTruthy();expect(CHART_COLORS.spo2).toBe('#2563eb')});
});
