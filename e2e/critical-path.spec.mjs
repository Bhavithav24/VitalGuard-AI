import { expect, test } from '@playwright/test';

const routes = [
  { path: '/#/dashboard', heading: 'Patient Monitoring Overview' },
  { path: '/#/patients', heading: 'Patients' },
  { path: '/#/alerts', heading: 'Alerts' },
  { path: '/#/analytics', heading: 'Analytics' },
  { path: '/#/settings', heading: 'Settings' },
];

test('all primary routes render and survive a browser reload', async ({ page }) => {
  for (const route of routes) {
    await page.goto(route.path);
    await expect(page).toHaveURL(new RegExp(route.path.replace(/[.*+?^${}()|[\]\\]/g, '\\    await page.goto(route.path);
    await expect(page.locator('#main-content')).toBeVisible();') + '
    await expect(page.locator('#main-content').getByRole('heading', { name: route.heading, exact: true }).first()).toBeVisible();

    await page.reload();
    await expect(page.locator('#main-content')).toBeVisible();
    await expect(page.locator('#main-content').getByRole('heading', { name: route.heading, exact: true }).first()).toBeVisible();
  }
});

test('primary navigation moves between core workspaces', async ({ page }) => {
  await page.goto('/#/dashboard');
  const navigation = page.getByRole('navigation', { name: 'Primary' });

  for (const route of routes.slice(1)) {
    await navigation.getByRole('link', { name: route.heading, exact: false }).click();
    await expect(page.locator('#main-content').getByRole('heading', { name: route.heading, exact: true }).first()).toBeVisible();
  }
});

test('mobile navigation opens and routes to Settings', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#/dashboard');
  await page.getByRole('button', { name: 'Open navigation menu' }).click();
  await page.getByRole('navigation', { name: 'Primary' }).getByRole('link', { name: 'Settings', exact: false }).click();
  await expect(page.locator('#main-content').getByRole('heading', { name: 'Settings', exact: true }).first()).toBeVisible();
});
));
    await expect(page.locator('#main-content')).toBeVisible();
    await expect(page.locator('#main-content').getByRole('heading', { name: route.heading, exact: true }).first()).toBeVisible();

    await page.reload();
    await expect(page.locator('#main-content')).toBeVisible();
    await expect(page.locator('#main-content').getByRole('heading', { name: route.heading, exact: true }).first()).toBeVisible();
  }
});

test('primary navigation moves between core workspaces', async ({ page }) => {
  await page.goto('/#/dashboard');
  const navigation = page.getByRole('navigation', { name: 'Primary' });

  for (const route of routes.slice(1)) {
    await navigation.getByRole('link', { name: route.heading, exact: false }).click();
    await expect(page.locator('#main-content').getByRole('heading', { name: route.heading, exact: true }).first()).toBeVisible();
  }
});

test('mobile navigation opens and routes to Settings', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#/dashboard');
  await page.getByRole('button', { name: 'Open navigation menu' }).click();
  await page.getByRole('navigation', { name: 'Primary' }).getByRole('link', { name: 'Settings', exact: false }).click();
  await expect(page.locator('#main-content').getByRole('heading', { name: 'Settings', exact: true }).first()).toBeVisible();
});
