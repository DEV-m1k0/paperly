document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const search = document.querySelector("#toolbar #searchbar");
  const breadcrumbs = document.querySelector(".content-header .breadcrumb");

  if (search && !search.placeholder) {
    search.placeholder = "Поиск по списку...";
  }

  // Improve readability of the last breadcrumb segment.
  if (breadcrumbs) {
    const last = breadcrumbs.querySelector("li:last-child");
    if (last) {
      last.classList.add("text-bold");
    }
  }

  // Mark long changelist pages for optional CSS behavior.
  if (document.querySelector(".change-list")) {
    body.classList.add("paperly-admin-changelist");
  }
});
