import { test, expect } from "@playwright/test";

test("создание кампании по форме ТЗ", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Создать кампанию" }).click();
  await page.getByLabel("Название кампании").fill("AU Test");
  await page.getByLabel("GEO", { exact: true }).fill("AU");
  await page.getByRole("combobox", { name: "Начальный оффер" }).fill("Alpha");
  await page.getByRole("option", { name: /Alpha/ }).click();
  await page.getByLabel("Домен", { exact: true }).selectOption("101");
  await page.getByLabel("Группа", { exact: true }).selectOption("102");
  await page.getByLabel("Источник", { exact: true }).selectOption("103");
  await page.getByRole("button", { name: "Create", exact: true }).click();
  await expect(page.getByRole("heading", { name: "AU Test" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "GEO", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Offers", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "Alpha", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "100%", exact: true }),
  ).toBeVisible();
});
