document.addEventListener("DOMContentLoaded", () => {
  const { apiJson, unwrapList } = window.paperly;
  window.paperly.renderCartCount();

  const searchForm = document.getElementById("searchForm");
  const profileForm = document.getElementById("profileForm");
  const addressForm = document.getElementById("addressForm");
  const notifyForm = document.getElementById("notifyForm");
  const userNamePreview = document.getElementById("userNamePreview");
  const userEmailPreview = document.getElementById("userEmailPreview");

  const state = { profileId: null, addressId: null, notifyId: null };

  function setValue(id, value) {
    const field = document.getElementById(id);
    if (!field) return;
    if (field.type === "checkbox") field.checked = Boolean(value);
    else if (value !== null && value !== undefined) field.value = value;
  }

  function updatePreview() {
    if (!userNamePreview || !userEmailPreview) return;
    const firstName = document.getElementById("firstName")?.value.trim() || "";
    const lastName = document.getElementById("lastName")?.value.trim() || "";
    const email = document.getElementById("email")?.value.trim() || "";
    const full = `${firstName} ${lastName}`.trim();
    if (full) userNamePreview.textContent = full;
    if (email) userEmailPreview.textContent = email;
  }

  function clearError(form) {
    form.querySelectorAll(".form-error").forEach((el) => el.remove());
    form.classList.remove("is-invalid");
  }

  function showError(form, text) {
    clearError(form);
    const msg = document.createElement("p");
    msg.className = "form-error";
    msg.textContent = text;
    form.append(msg);
    form.classList.add("is-invalid");
  }

  async function loadProfile() {
    try {
      const rows = unwrapList(await apiJson("/api/profiles/"));
      if (!rows.length) return null;
      const profile = rows[0];
      state.profileId = profile.id;

      if (!document.getElementById("firstName")?.value) {
        setValue("firstName", profile.first_name || profile.user_first_name || "");
      }
      if (!document.getElementById("lastName")?.value) {
        setValue("lastName", profile.last_name || profile.user_last_name || "");
      }
      if (!document.getElementById("phone")?.value) {
        setValue("phone", profile.phone || "");
      }
      if (!document.getElementById("birthDate")?.value && profile.birth_date) {
        const bdInput = document.getElementById("birthDate");
        if (bdInput && bdInput._flatpickr) bdInput._flatpickr.setDate(profile.birth_date, true);
        else setValue("birthDate", profile.birth_date || "");
      }
      if (!document.getElementById("email")?.value && (profile.user_email || profile.email)) {
        setValue("email", profile.user_email || profile.email);
      }
      updatePreview();
      return profile;
    } catch (error) {
      console.error("Profile API error", error);
      return null;
    }
  }

  async function loadAddress() {
    try {
      const rows = unwrapList(await apiJson("/api/addresses/"));
      if (!rows.length) return null;
      const address = rows.find((item) => item.is_default) || rows[0];
      state.addressId = address.id;

      if (!document.getElementById("city")?.value) setValue("city", address.city || "");
      if (!document.getElementById("street")?.value) setValue("street", address.street || "");
      if (!document.getElementById("entrance")?.value) setValue("entrance", address.entrance || "");
      if (!document.getElementById("flat")?.value) setValue("flat", address.flat_or_office || "");
      if (!document.getElementById("comment")?.value) setValue("comment", address.comment || "");
      return address;
    } catch (error) {
      console.error("Address API error", error);
      return null;
    }
  }

  async function loadNotifications() {
    try {
      const rows = unwrapList(await apiJson("/api/notification-settings/"));
      if (!rows.length) return null;
      const notify = rows[0];
      state.notifyId = notify.id;
      setValue("nOrder", notify.order_status);
      setValue("nPromo", notify.promotions);
      setValue("nRestock", notify.restock);
      return notify;
    } catch (error) {
      console.error("Notifications API error", error);
      return null;
    }
  }

  async function ensureProfile() {
    if (state.profileId) return state.profileId;
    const payload = {
      first_name: document.getElementById("firstName")?.value.trim() || "",
      last_name: document.getElementById("lastName")?.value.trim() || "",
      phone: document.getElementById("phone")?.value.trim() || "",
      birth_date: document.getElementById("birthDate")?.value || null,
      email: document.getElementById("email")?.value.trim() || "",
    };
    const profile = await apiJson("/api/profiles/", { method: "POST", body: payload });
    state.profileId = profile.id;
    return profile.id;
  }

  function handleSubmit(form, buttonText, handler) {
    if (!form) return;
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearError(form);
      if (!form.checkValidity()) {
        showError(form, "Пожалуйста, заполните обязательные поля корректно.");
        return;
      }
      const button = form.querySelector("button[type='submit']");
      const initial = button.textContent;
      button.textContent = "Сохраняем...";
      button.disabled = true;

      try {
        await handler();
        updatePreview();
        button.textContent = buttonText;
      } catch (error) {
        console.error("Profile save error", error);
        showError(form, "Не удалось сохранить данные. Попробуйте еще раз.");
        button.textContent = initial;
      } finally {
        setTimeout(() => {
          button.textContent = initial;
          button.disabled = false;
        }, 1000);
      }
    });
  }

  handleSubmit(profileForm, "Сохранено", async () => {
    const payload = {
      first_name: document.getElementById("firstName")?.value.trim() || "",
      last_name: document.getElementById("lastName")?.value.trim() || "",
      phone: document.getElementById("phone")?.value.trim() || "",
      birth_date: document.getElementById("birthDate")?.value || null,
      email: document.getElementById("email")?.value.trim() || "",
    };
    if (state.profileId) {
      await apiJson(`/api/profiles/${state.profileId}/`, { method: "PATCH", body: payload });
    } else {
      await ensureProfile();
    }
  });

  handleSubmit(addressForm, "Адрес сохранен", async () => {
    const profileId = await ensureProfile();
    const payload = {
      profile: profileId,
      address_type: "shipping",
      city: document.getElementById("city")?.value.trim() || "",
      street: document.getElementById("street")?.value.trim() || "",
      entrance: document.getElementById("entrance")?.value.trim() || "",
      flat_or_office: document.getElementById("flat")?.value.trim() || "",
      comment: document.getElementById("comment")?.value.trim() || "",
      is_default: true,
    };
    const url = state.addressId ? `/api/addresses/${state.addressId}/` : "/api/addresses/";
    const method = state.addressId ? "PATCH" : "POST";
    const saved = await apiJson(url, { method, body: payload });
    state.addressId = saved.id;
  });

  handleSubmit(notifyForm, "Настройки сохранены", async () => {
    const profileId = await ensureProfile();
    const payload = {
      profile: profileId,
      order_status: Boolean(document.getElementById("nOrder")?.checked),
      promotions: Boolean(document.getElementById("nPromo")?.checked),
      restock: Boolean(document.getElementById("nRestock")?.checked),
    };
    const url = state.notifyId ? `/api/notification-settings/${state.notifyId}/` : "/api/notification-settings/";
    const method = state.notifyId ? "PATCH" : "POST";
    const saved = await apiJson(url, { method, body: payload });
    state.notifyId = saved.id;
  });

  profileForm?.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", updatePreview);
  });

  searchForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
  });

  (async () => {
    await loadProfile();
    await loadAddress();
    await loadNotifications();
    updatePreview();
  })();
});
