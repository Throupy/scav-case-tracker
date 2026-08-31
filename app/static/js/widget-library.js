(function () {
    'use strict';

    const WIDGET_CATALOGUE = [
        { id: 'kpi_total_cases',               title: 'Total Cases',            icon: 'fa-clipboard-list', defaultW: 3, defaultH: 1, minW: 2 },
        { id: 'kpi_total_profit',              title: 'Total Profit',           icon: 'fa-coins',          defaultW: 3, defaultH: 1, minW: 2 },
        { id: 'kpi_total_spent',               title: 'Total Spent',            icon: 'fa-money-bill-wave',defaultW: 3, defaultH: 1, minW: 2 },
        { id: 'kpi_total_return',              title: 'Total Return',           icon: 'fa-arrow-up',       defaultW: 3, defaultH: 1, minW: 2 },
        { id: 'kpi_most_common_item_type',     title: 'Most Common Item',       icon: 'fa-box',            defaultW: 3, defaultH: 1, minW: 2 },
        { id: 'kpi_top_contributor',           title: 'Top Contributor',        icon: 'fa-user',           defaultW: 3, defaultH: 1, minW: 2 },
        { id: 'kpi_most_profitable_case_type', title: 'Most Profitable Case',   icon: 'fa-chart-line',     defaultW: 3, defaultH: 1, minW: 2 },
        { id: 'kpi_most_valuable_item',        title: 'Most Valuable Item',     icon: 'fa-gem',            defaultW: 3, defaultH: 1, minW: 2 },
        { id: 'kpi_biggest_loss',              title: 'Biggest Loss',           icon: 'fa-chart-pie',      defaultW: 3, defaultH: 1, minW: 2 },
        { id: 'kpi_win_rate',                  title: 'Win Rate',               icon: 'fa-chart-line',     defaultW: 3, defaultH: 1, minW: 2 },
        { id: 'kpi_average_roi',               title: 'Average ROI',            icon: 'fa-chart-pie',      defaultW: 3, defaultH: 1, minW: 2 },
        { id: 'chart_earnings_overview',       title: 'Earnings Overview',      icon: 'fa-chart-line',     defaultW: 8, defaultH: 3, minW: 6 },
        { id: 'chart_case_distribution',       title: 'Case Type Distribution', icon: 'fa-chart-pie',      defaultW: 4, defaultH: 3, minW: 3 },
    ];

    let _grid   = null;
    let _locked = true;
    let _hidden = {};

    function getHiddenDefs() {
        return WIDGET_CATALOGUE.filter(function (w) { return !!_hidden[w.id]; });
    }

    function persistLayout() {
        var layout = (_grid.save(false) || [])
            .filter(function (n) { return n.id; })
            .map(function (n) { return { id: n.id, x: n.x, y: n.y, w: n.w, h: n.h }; });

        fetch('/cases/global-dashboard/layout', {
            method: 'PUT',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': (document.querySelector('meta[name="csrf-token"]') || {}).getAttribute('content')
            },
            body: JSON.stringify({ layout: layout })
        });
    }

    function hideWidget(id) {
        var el = _grid.el.querySelector('[gs-id="' + id + '"]');
        if (!el) return;

        _grid.removeWidget(el, false);
        removeRemoveBtn(el);
        el.style.display = 'none';
        _hidden[id] = el;

        persistLayout();
        renderModal();
    }

    function showWidget(id) {
        var el = _hidden[id];
        if (!el) return;

        var def = WIDGET_CATALOGUE.find(function (w) { return w.id === id; });
        if (!def) return;

        delete _hidden[id];

        delete el._gridstackNode;
        delete el.gridstackNode;
        el.style.cssText = '';

        el.setAttribute('gs-w',     String(def.defaultW));
        el.setAttribute('gs-h',     String(def.defaultH));
        el.setAttribute('gs-min-w', String(def.minW));
        el.removeAttribute('gs-x');
        el.removeAttribute('gs-y');

        _grid.makeWidget(el);

        if (!_locked) addRemoveBtn(el);
        persistLayout();
        renderModal();
    }

    function addRemoveBtn(el) {
        var id = el.getAttribute('gs-id');
        if (!id || el.querySelector('.widget-remove-btn')) return;
        var content = el.querySelector('.grid-stack-item-content');
        if (!content) return;

        var btn = document.createElement('button');
        btn.className = 'widget-remove-btn';
        btn.title     = 'Remove widget';
        btn.innerHTML = '<i class="fas fa-times fa-xs"></i>';
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            hideWidget(id);
        });
        content.appendChild(btn);
    }

    function removeRemoveBtn(el) {
        var b = el.querySelector('.widget-remove-btn');
        if (b) b.remove();
    }

    function addAllRemoveBtns() {
        _grid.el.querySelectorAll('.grid-stack-item').forEach(function (el) {
            if (el.style.display !== 'none') addRemoveBtn(el);
        });
    }

    function removeAllRemoveBtns() {
        _grid.el.querySelectorAll('.widget-remove-btn').forEach(function (b) { b.remove(); });
    }

    function renderModal() {
        var container = document.getElementById('widget-library-grid');
        if (!container) return;

        var hidden = getHiddenDefs();

        if (hidden.length === 0) {
            container.innerHTML =
                '<div class="col-12 text-center text-muted py-4">' +
                    '<i class="fas fa-check-circle fa-2x mb-2 text-success d-block"></i>' +
                    'All widgets are on your dashboard!' +
                '</div>';
            return;
        }

        container.innerHTML = hidden.map(function (w) {
            return (
                '<div class="col-sm-6 col-md-4 mb-3">' +
                    '<div class="card widget-library-tile h-100" data-widget-id="' + w.id + '">' +
                        '<div class="card-body text-center py-3">' +
                            '<i class="fas ' + w.icon + ' fa-2x mb-2 text-danger"></i>' +
                            '<p class="mb-2 small font-weight-bold">' + w.title + '</p>' +
                            '<button class="btn btn-sm btn-outline-danger btn-add-widget"' +
                                ' data-widget-id="' + w.id + '">' +
                                '<i class="fas fa-plus fa-xs mr-1"></i>Add' +
                            '</button>' +
                        '</div>' +
                    '</div>' +
                '</div>'
            );
        }).join('');

        container.querySelectorAll('.btn-add-widget').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var id = this.dataset.widgetId;
                showWidget(id);
                if (getHiddenDefs().length === 0) {
                    $('#widgetLibraryModal').modal('hide');
                }
            });
        });
    }

    function init(grid, savedLayout) {
        _grid  = grid;
        _hidden = {};

        var libraryBtn = document.getElementById('widget-library-btn');
        if (libraryBtn) {
            libraryBtn.addEventListener('click', function () {
                $('#widgetLibraryModal').modal('show');
            });
        }

        if (Array.isArray(savedLayout) && savedLayout.length > 0) {
            var savedIds = new Set(savedLayout.map(function (n) { return n.id; }));
            WIDGET_CATALOGUE.forEach(function (w) {
                if (!savedIds.has(w.id)) {
                    var el = _grid.el.querySelector('[gs-id="' + w.id + '"]');
                    if (el) {
                        _grid.removeWidget(el, false);
                        el.style.display = 'none';
                        _hidden[w.id] = el;
                    }
                }
            });
        }

        renderModal();
    }

    function setLocked(locked) {
        _locked = locked;

        var libraryBtn = document.getElementById('widget-library-btn');
        if (libraryBtn) libraryBtn.style.display = locked ? 'none' : '';

        if (locked) {
            removeAllRemoveBtns();
        } else {
            addAllRemoveBtns();
        }
    }

    window.WidgetLibrary = { init: init, setLocked: setLocked };
})();
