const sidebar = document.querySelector("#admin-sidebar");
document.querySelector("[data-admin-menu-open]")?.addEventListener("click", () => {
  sidebar?.classList.remove("hidden");
});
document.querySelector("[data-admin-menu-close]")?.addEventListener("click", () => {
  sidebar?.classList.add("hidden");
});

document.querySelectorAll("[data-confirm]").forEach((button) => {
  button.addEventListener("click", (event) => {
    if (!window.confirm(button.dataset.confirm)) event.preventDefault();
  });
});

const tableSearch = document.querySelector("[data-table-search]");
const tableFilter = document.querySelector("[data-table-filter]");
const tableRows = [...document.querySelectorAll("[data-table-row]")];
function filterAdminTable() {
  const needle = tableSearch?.value.toLowerCase() || "";
  const filter = tableFilter?.value || "";
  tableRows.forEach((row) => {
    row.hidden =
      !row.dataset.search.toLowerCase().includes(needle) ||
      (filter && row.dataset.filter !== filter);
  });
}
tableSearch?.addEventListener("input", filterAdminTable);
tableFilter?.addEventListener("change", filterAdminTable);
