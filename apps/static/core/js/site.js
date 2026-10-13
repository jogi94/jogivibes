document.addEventListener("click", (event) => {
    const trigger = event.target.closest("#mobile-menu-trigger");

    if (!trigger) {
        return;
    }

    const menu = document.getElementById("mobile-navigation");

    if (!menu) {
        return;
    }

    const isOpen = trigger.getAttribute("aria-expanded") === "true";
    const nextState = !isOpen;

    trigger.setAttribute("aria-expanded", String(nextState));

    trigger.setAttribute(
        "aria-label",
        nextState
            ? "Close navigation menu"
            : "Open navigation menu"
    );

    menu.hidden = !nextState;
});