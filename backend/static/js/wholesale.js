document.addEventListener("DOMContentLoaded", () => {
  const searchForm = document.getElementById("searchForm");
  const requestForm = document.getElementById("requestForm");

  if (searchForm) {
    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const query = searchForm.querySelector("input")?.value.trim();
      if (query) {
        window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
      }
    });
  }

  if (requestForm) {
    requestForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const button = requestForm.querySelector("button[type='submit']");
      const initialText = button.textContent;
      button.textContent = "Отправка...";
      button.disabled = true;

      const payload = {
        organization_name: requestForm.querySelector("input[type='text']")?.value.trim() || "",
        contact_person: requestForm.querySelectorAll("input[type='text']")[1]?.value.trim() || "",
        phone: requestForm.querySelector("input[type='tel']")?.value.trim() || "",
        email: requestForm.querySelector("input[type='email']")?.value.trim() || "",
        comment: requestForm.querySelector("textarea")?.value.trim() || "",
      };

      try {
        await window.paperly.apiJson("/api/wholesale-requests/", { method: "POST", body: payload });
        button.textContent = "Заявка отправлена!";
        setTimeout(() => {
          button.textContent = initialText;
          button.disabled = false;
          requestForm.reset();
        }, 2000);
      } catch (error) {
        console.error("Wholesale request error:", error);
        button.textContent = "Ошибка отправки";
        setTimeout(() => {
          button.textContent = initialText;
          button.disabled = false;
        }, 2000);
      }
    });
  }
});
