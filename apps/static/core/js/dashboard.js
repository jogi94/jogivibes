document.addEventListener("click", function (event) {
    const menuButton = event.target.closest(".dashboard-menu-toggle");

    if (!menuButton) return;

    const dashboard = menuButton.closest(".dashboard");
    if (!dashboard) return;

    const isOpen = dashboard.classList.toggle("sidebar-open");

    menuButton.setAttribute("aria-expanded", String(isOpen));
});