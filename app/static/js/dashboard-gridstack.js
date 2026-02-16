// Rudimentary to-do list for the gridstack
// TODO: Implement passing to flask backend for storage
// TODO: Resizable?
// TODO: 'widget library' to select
// TODO: Ability to remove widgets from view - drag away, or X button when unlocked
// TODO: Resizing - auto text-wrap

(function () {
  const STORAGE_KEY = "dashboard_layout_v1";

  const grid = GridStack.init({
    column: 12,
    margin: "12px 12px",
    cellHeight: 130,
    float: false,
    // disableResize: true,
    animate: true,
    
    resizable: { handles: "all" },
    draggable: true
  }, ".grid-stack");

  function loadLayout() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const layout = JSON.parse(raw);
      return Array.isArray(layout) ? layout : null;
    } catch {
      return null;
    }
  }

  function saveLayout() {
    const layout = grid.save(false).map(n => ({
      id: n.id,
      x: n.x, y: n.y, w: n.w, h: n.h
    }));
    // TODO: Pass back to Flask for storage in the database, against the User object
    // Using localStorage for a 'proof of concept'
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
  }

  function applyLayout(layout) {
    grid.load(layout);
  }

  function nudgeCharts() {
    if (Array.isArray(window._charts)) {
      window._charts.forEach(ch => {
        try { ch.resize(); } catch {}
      });
    }
    window.dispatchEvent(new Event("resize"));
  }

  let locked = true;
  const btn = document.getElementById("toggle-layout-btn");

  function setLocked(state) {
    locked = state;
    grid.setStatic(locked);

    btn.textContent = locked ? "Unlock layout" : "Lock layout";
  }
  setLocked(true);

  btn.addEventListener("click", function () {
    setLocked(!locked);
  });

  const stored = loadLayout();
  if (stored) {
    applyLayout(stored);
    setTimeout(nudgeCharts, 50);
  }

  grid.on("dragstop", function () {
    saveLayout();
    nudgeCharts();
  });

  grid.on("resizestop", function () {
    saveLayout();
    nudgeCharts();
  });
})();
