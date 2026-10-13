
document.addEventListener("DOMContentLoaded", () => {
    const heroSection = document.querySelector(".hero-section");
    const carousel = document.querySelector(".hero-carousel");
    const track = document.querySelector(".hero-card-track");

    let currentBackground = document.querySelector(
        ".hero-background-current"
    );

    let nextBackground = document.querySelector(
        ".hero-background-next"
    );

    const heroTitle = document.querySelector(".hero-title");
    const heroDescription = document.querySelector(".hero-description");
    const carouselTitle = document.querySelector(".hero-carousel-title");
    const currentSlide = document.querySelector(".current-slide");

    const indicatorDots = Array.from(
        document.querySelectorAll(".indicator-dot")
    );

    if (
        !heroSection ||
        !carousel ||
        !track ||
        !heroTitle ||
        !heroDescription
    ) {
        return;
    }

    const cards = Array.from(
        track.querySelectorAll(".hero-trip-card")
    );

    if (cards.length < 2) {
        return;
    }

    const slideDuration = 2000;
    const animationDuration = 650;
    const backgroundDuration = 900;

    let isAnimating = false;
    let rotationIndex = 0;
    let rotationTimer = null;

    /*
     * A = initial main hero.
     * The carousel cards supply the remaining destinations.
     */
    const heroDestination = {
        title: heroTitle.textContent.trim(),
        description: heroDescription.textContent.trim(),
        background: currentBackground
            ? getComputedStyle(currentBackground).backgroundImage
            : ""
    };

    function readCard(card) {
        const image = card.querySelector("img");
        const caption = card.querySelector(".hero-card-caption");

        return {
            title: card.dataset.title || "",
            description: card.dataset.description || "",
            background: card.dataset.background || "",
            image: image ? image.getAttribute("src") || "" : "",
            alt: image ? image.alt || "" : "",
            caption: caption ? caption.textContent.trim() : ""
        };
    }

    /*
     * Keep the existing cyclic sequence:
     * initial hero + all carousel destinations.
     */
    const destinations = [
        heroDestination,
        ...cards.map(readCard)
    ];

    function setCardContent(card, destination) {
        if (!card || !destination) {
            return;
        }

        card.dataset.title = destination.title;
        card.dataset.description = destination.description;
        card.dataset.background = destination.background;

        const image = card.querySelector("img");
        const caption = card.querySelector(".hero-card-caption");

        if (image) {
            image.src = destination.image || destination.background;
            image.alt = destination.alt || destination.title;
        }

        if (caption) {
            caption.textContent =
                destination.caption || destination.title;
        }
    }

    /*
     * Keep exactly one card active.
     * The active card is larger; all other cards are smaller.
     */
    function updateActiveCard() {
        const visibleCards = Array.from(
            track.querySelectorAll(".hero-trip-card")
        );

        visibleCards.forEach((card, index) => {
            card.classList.toggle("active", index === 0);
        });
    }

    function normalizeBackground(background) {
        if (!background) {
            return "";
        }

        const value = background.trim();

        return value.startsWith("url(")
            ? value
            : `url("${value}")`;
    }

    function updateBackground(background) {
        if (!background || !currentBackground || !nextBackground) {
            return;
        }

        const normalizedBackground = normalizeBackground(background);

        if (
            currentBackground.style.backgroundImage ===
            normalizedBackground
        ) {
            return;
        }

        /*
         * Prepare the next background layer.
         */
        nextBackground.style.transition = "none";
        nextBackground.style.opacity = "0";
        nextBackground.style.backgroundImage = normalizedBackground;

        void nextBackground.offsetHeight;

        /*
         * Start the background crossfade immediately.
         */
        nextBackground.style.transition =
            `opacity ${backgroundDuration}ms ease-in-out`;

        nextBackground.style.opacity = "1";

        /*
         * Swap the layer references.
         */
        const previousBackground = currentBackground;

        currentBackground = nextBackground;
        nextBackground = previousBackground;

        currentBackground.classList.remove("hero-background-next");
        currentBackground.classList.add("hero-background-current");

        nextBackground.classList.remove("hero-background-current");
        nextBackground.classList.add("hero-background-next");

        nextBackground.style.opacity = "0";
    }

    function updateHero(destination) {
        if (!destination) {
            return;
        }

        const needsUpdate =
            heroTitle.textContent !== destination.title ||
            heroDescription.textContent !== destination.description;

        /*
         * Fade the heading and description during card movement.
         */
        if (needsUpdate) {
            heroTitle.classList.add("is-changing");
            heroDescription.classList.add("is-changing");

            window.setTimeout(() => {
                heroTitle.textContent = destination.title;
                heroDescription.textContent = destination.description;

                requestAnimationFrame(() => {
                    heroTitle.classList.remove("is-changing");
                    heroDescription.classList.remove("is-changing");
                });
            }, 350);
        }

        /*
         * Start the background transition at the same time.
         */
        updateBackground(destination.background);
    }

    function updateIndicators() {
        if (indicatorDots.length === 0) {
            return;
        }

        const activeIndex = rotationIndex % indicatorDots.length;

        indicatorDots.forEach((dot, index) => {
            const active = index === activeIndex;

            dot.classList.toggle("active", active);

            dot.setAttribute(
                "aria-current",
                active ? "true" : "false"
            );
        });

        if (currentSlide) {
            currentSlide.textContent = String(
                activeIndex + 1
            ).padStart(2, "0");
        }
    }

    function revealHero() {
        heroSection.classList.add("is-ready");
        carousel.classList.add("is-ready");
    }

    /*
     * Reset the track without animating its position.
     */
    function resetTrackPosition() {
        track.style.transition = "none";
        track.style.transform = "translateX(0)";

        void track.offsetHeight;
    }

    function rotateCarousel() {
        if (isAnimating) {
            return;
        }

        const firstCard = track.firstElementChild;

        if (!firstCard) {
            return;
        }

        isAnimating = true;

        const trackStyles = getComputedStyle(track);

        const gap =
            parseFloat(trackStyles.columnGap) ||
            parseFloat(trackStyles.gap) ||
            0;

        /*
         * Use the layout width, not the visually scaled width.
         */
        const distance = firstCard.offsetWidth + gap;

        /*
         * Begin card movement.
         */
        track.style.transition =
            `transform ${animationDuration}ms ease-in-out`;

        track.style.transform = `translateX(-${distance}px)`;

        /*
         * Update the main hero at the START of movement.
         */
        const nextRotationIndex =
            (rotationIndex + 1) % destinations.length;

        updateHero(destinations[nextRotationIndex]);

        function finishSlide(event) {
            if (
                event.target !== track ||
                event.propertyName !== "transform"
            ) {
                return;
            }

            track.removeEventListener(
                "transitionend",
                finishSlide
            );

            /*
             * Advance the cyclic destination index.
             */
            rotationIndex =
                (rotationIndex + 1) % destinations.length;

            const outgoingHero = destinations[
                (rotationIndex - 1 + destinations.length) %
                destinations.length
            ];

            /*
             * Reset the track before changing the DOM order.
             */
            resetTrackPosition();

            /*
             * Move the outgoing first card to the end.
             */
            track.appendChild(firstCard);

            /*
             * Apply the new order before restoring the transition.
             */
            void track.offsetHeight;

            track.style.transition =
                `transform ${animationDuration}ms ease-in-out`;

            /*
             * Update card content for the new cycle.
             */
            const orderedCards = Array.from(
                track.querySelectorAll(".hero-trip-card")
            );

            orderedCards.forEach((card, index) => {
                const destinationIndex =
                    (rotationIndex + index + 1) %
                    destinations.length;

                const destination = destinations[destinationIndex];

                if (destination) {
                    setCardContent(card, destination);
                }
            });

            /*
             * The outgoing main hero becomes the final card.
             */
            const lastCard = track.lastElementChild;

            if (lastCard) {
                setCardContent(lastCard, outgoingHero);
            }

            /*
             * NEW: make only the first card active.
             * Its larger size will move forward with each rotation.
             */
            updateActiveCard();

            /*
             * Update the carousel title and indicators.
             * The main hero was already updated at movement start.
             */
            if (carouselTitle) {
                carouselTitle.textContent =
                    track.firstElementChild?.dataset.title || "";
            }

            updateIndicators();

            isAnimating = false;
        }

        track.addEventListener(
            "transitionend",
            finishSlide
        );
    }

    /*
     * Initialize the first active card and indicator state.
     */
    updateActiveCard();
    updateIndicators();

    /*
     * Reveal the hero after the page finishes loading.
     */
    if (document.readyState === "complete") {
        requestAnimationFrame(revealHero);
    } else {
        window.addEventListener(
            "load",
            () => {
                requestAnimationFrame(revealHero);
            },
            { once: true }
        );
    }

    /*
     * Preserve automatic carousel rotation.
     */
    rotationTimer = window.setInterval(
        rotateCarousel,
        slideDuration
    );

    console.log(
        "Jogi Vibes cyclic hero carousel initialized."
    );
});
