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
      if (!requestForm.checkValidity()) {
        requestForm.reportValidity();
        return;
      }

      const button = requestForm.querySelector("button[type='submit']");
      const initialText = button.textContent;
      button.textContent = "Отправка...";
      button.disabled = true;

      const formData = new FormData(requestForm);
      const payload = {
        organization_name: formData.get("organization_name")?.trim() || "",
        organization_type: formData.get("organization_type") || "other",
        contact_person: formData.get("contact_person")?.trim() || "",
        phone: formData.get("phone")?.trim() || "",
        email: formData.get("email")?.trim() || "",
        comment: formData.get("comment")?.trim() || "",
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
