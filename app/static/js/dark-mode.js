(function () {
    const key = "darkMode";
    const root = document.documentElement;
  
    function isDark() {
      return root.classList.contains("dark");
    }
  
    function setDark(on) {
      root.classList.toggle("dark", on);
    }
  
    function updateText() {
      const toggleText = document.getElementById("themeToggleText");
      if (!toggleText) return;
      toggleText.textContent = isDark() ? "Switch to Light Mode" : "Switch to Dark Mode";
    }
  
    // Apply saved mode (safe even if head script already did it)
    setDark(localStorage.getItem(key) === "on");
    updateText();
  
    // Wire up toggle if it exists on this page
    document.addEventListener("click", function (e) {
      const toggleItem = e.target.closest("#themeToggleItem");
      if (!toggleItem) return;
  
      e.preventDefault();
  
      const newState = !isDark();
      localStorage.setItem(key, newState ? "on" : "off");
      setDark(newState);
      updateText();
  
      document.dispatchEvent(new CustomEvent("theme:changed"));
    });
  })();
  