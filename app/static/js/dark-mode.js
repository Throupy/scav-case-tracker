(function () {
    const key = "darkMode";
    const body = document.body;
    const toggleItem = document.getElementById("themeToggleItem");
    const toggleText = document.getElementById("themeToggleText");
  
    if (!toggleItem || !toggleText) return;
  
    function isDark() {
      return body.classList.contains("dark");
    }
  
    function apply(isDarkMode) {
      if (isDarkMode) {
        body.classList.add("dark");
      } else {
        body.classList.remove("dark");
      }
      updateText();
    }
  
    function updateText() {
      toggleText.textContent = isDark()
        ? "Switch to Light Mode"
        : "Switch to Dark Mode";
    }
  
    const saved = localStorage.getItem(key);
    apply(saved === "on");
  
    toggleItem.addEventListener("click", function (e) {
      e.preventDefault();
  
      const newState = !isDark();
      localStorage.setItem(key, newState ? "on" : "off");
      apply(newState);
      document.dispatchEvent(new CustomEvent("theme:changed"));
    });
  })();
  