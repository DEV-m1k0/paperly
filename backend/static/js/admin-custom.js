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

  // Remove any "jazzmin" mentions from the page
  function removeJazzminText(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      if (/jazzmin/i.test(node.textContent)) {
        node.textContent = node.textContent.replace(/jazzmin/gi, "Paperly");
      }
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      node.childNodes.forEach(removeJazzminText);
    }
  }
  removeJazzminText(document.body);

  // Hide jazzmin version badge in footer
  document.querySelectorAll("a[href*='jazzmin'], span, small, .badge").forEach((el) => {
    if (/jazzmin/i.test(el.textContent)) {
      el.style.display = "none";
    }
  });
});
