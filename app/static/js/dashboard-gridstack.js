// Rudimentary to-do list for the gridstack
// TODO: 'widget library' to select
// TODO: Ability to remove widgets from view - drag away, or X button when unlocked
// TODO: Resizing - auto text-wrap

(function () {
  const gridEl = document.querySelector(".grid-stack");
  if (!gridEl) return;

  const isAuthenticated = window.IS_AUTHENTICATED === true || window.IS_AUTHENTICATED === "true";
  const btn = document.getElementById("toggle-layout-btn");

  const grid = GridStack.init({
    column: 12,
    margin: "12px",
    cellHeight: 130,
    float: false,
    animate: true,
    draggable: isAuthenticated,   // only draggable if logged in
    resizable: isAuthenticated ? { handles: "all" } : false
  }, ".grid-stack");

  function nudgeCharts() {
    if (Array.isArray(window._charts)) {
      window._charts.forEach(ch => {
        try { ch.resize(); } catch {}
      });
    }
    window.dispatchEvent(new Event("resize"));
  }

  function getLayout() {
    return grid.save(false).map(n => ({
      id: n.id,
      x: n.x,
      y: n.y,
      w: n.w,
      h: n.h
    }));
  }

  async function saveLayout(layout) {
    await fetch("/cases/global-dashboard/layout", {
      method: "PUT",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": document
          .querySelector('meta[name="csrf-token"]')
          ?.getAttribute("content")
      },
      body: JSON.stringify({ layout })
    });
  }

  async function loadLayout() {
    const res = await fetch("/cases/global-dashboard/layout", {
      credentials: "include"
    });

    if (!res.ok) return null;
    return await res.json();
  }

  if (isAuthenticated) {

    let locked = true;

    function setLocked(state) {
      locked = state;
      grid.enableMove(!locked);
      grid.enableResize(!locked);
      if (btn) {
        btn.textContent = locked ? "Unlock layout" : "Lock layout";
      }
    }

    if (btn) {
      btn.addEventListener("click", () => setLocked(!locked));
    }

    (async function boot() {
      const stored = await loadLayout();
      if (Array.isArray(stored) && stored.length) {
        grid.load(stored);
      }
      setLocked(true);
      setTimeout(nudgeCharts, 50);
    })();

    function persist() {
      const layout = getLayout();
      saveLayout(layout);
      nudgeCharts();
    }

    grid.on("dragstop", persist);
    grid.on("resizestop", persist);
  }

  else {
    grid.enableMove(false);
    grid.enableResize(false);
    setTimeout(nudgeCharts, 50);
  }

})();

