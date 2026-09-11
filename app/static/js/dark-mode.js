(function () {
    const root = document.documentElement;
    const accountId = root.dataset.accountId || "guest";
    const storageKey = "appearance:" + accountId;
    const modes = ["light", "dark"];
    const accents = ["red", "blue", "green", "purple", "amber"];

    function readPreference() {
      let saved = {};
      try { saved = JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch (_) {}
      const legacyDark = localStorage.getItem("darkMode") === "on";
      return {
        mode: modes.includes(saved.mode) ? saved.mode : (legacyDark ? "dark" : "light"),
        accent: accents.includes(saved.accent) ? saved.accent : "red"
      };
    }

    function updateControls(preference) {
      document.querySelectorAll("[data-mode-option]").forEach(function (button) {
        const selected = button.dataset.modeOption === preference.mode;
        button.classList.toggle("active", selected);
        button.setAttribute("aria-pressed", selected ? "true" : "false");
      });
      document.querySelectorAll("[data-accent-option]").forEach(function (button) {
        const selected = button.dataset.accentOption === preference.accent;
        button.classList.toggle("active", selected);
        button.setAttribute("aria-pressed", selected ? "true" : "false");
      });
    }

    function applyPreference(preference, persist) {
      root.dataset.mode = preference.mode;
      root.dataset.accent = preference.accent;
      root.classList.toggle("dark", preference.mode === "dark");
      if (persist) {
        localStorage.setItem(storageKey, JSON.stringify(preference));
        localStorage.removeItem("darkMode");
      }
      updateControls(preference);
      window.appAppearance = preference;
      document.dispatchEvent(new CustomEvent("theme:changed", { detail: preference }));
    }

    window.themeAccent = function (alpha) {
      const styles = getComputedStyle(root);
      if (typeof alpha === "number") {
        return "rgba(" + styles.getPropertyValue("--accent-rgb").trim() + ", " + alpha + ")";
      }
      return styles.getPropertyValue("--accent").trim() || "#e74a3b";
    };

    let preference = readPreference();
    applyPreference(preference, false);

    document.addEventListener("click", function (event) {
      const modeButton = event.target.closest("[data-mode-option]");
      const accentButton = event.target.closest("[data-accent-option]");
      if (!modeButton && !accentButton) return;

      if (modeButton) preference.mode = modeButton.dataset.modeOption;
      if (accentButton) preference.accent = accentButton.dataset.accentOption;
      applyPreference(preference, true);
    });

    document.addEventListener("DOMContentLoaded", function () {
      updateControls(preference);
    });
})();
