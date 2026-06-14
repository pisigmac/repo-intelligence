import { test, expect } from '@playwright/test'

test('dashboard loads and sidebar navigation works', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/Repo Intelligence/)
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()

  await page.getByRole('link', { name: 'Capabilities' }).click()
  await expect(page).toHaveURL(/\/capabilities/)

  await page.getByRole('link', { name: 'Playbooks' }).click()
  await expect(page).toHaveURL(/\/playbooks/)
})
