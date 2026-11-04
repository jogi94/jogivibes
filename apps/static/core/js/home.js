
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
    const heroExplore = document.querySelector(".hero-cta");
    const currentSlide = document.querySelector(".current-slide");

    const indicatorDots = Array.from(
        document.querySelectorAll(".indicator-dot")
    );

    if (!heroSection || !heroTitle || !heroDescription) {
        return;
    }

    const heroCopy = document.querySelector(".hero-copy");

    // Read the initial hero category.
    const heroDestination = {
        title: heroTitle.textContent.trim(),
        description: heroDescription.textContent.trim(),
        category: heroCopy?.dataset.category || "",
        background: currentBackground
            ? getComputedStyle(currentBackground).backgroundImage
            : "",
        image: heroCopy?.dataset.image || "",
        alt: heroCopy?.dataset.imageAlt || heroTitle.textContent.trim(),
        caption: heroTitle.textContent.trim(),
    };

    // Update Explore URL for the active category.
    const exploreBaseUrl = heroExplore?.getAttribute("href");

    function updateExploreLink(category) {
        if (!heroExplore || !exploreBaseUrl) {
            return;
        }
        const url = new URL(exploreBaseUrl, window.location.origin);
        if (category) {
            url.searchParams.set("category", category);
        } else {
            url.searchParams.delete("category");
        }
        heroExplore.href = `${url.pathname}${url.search}`;
    }

    // Initialize the first category CTA immediately.
    updateExploreLink(heroDestination.category);

    if (!carousel || !track) {
        return;
    }

    const cards = Array.from(
        track.querySelectorAll(".hero-trip-card")
    );

    if (cards.length === 0) {
        return;
    }

    const slideDuration = 2000;
    const animationDuration = 650;
    const backgroundDuration = 900;

    let isAnimating = false;
    let rotationIndex = 0;

    // Read category card data.
    function readCard(card) {
        const image = card.querySelector("img");
        const caption = card.querySelector(".hero-card-caption");

        return {
            title: card.dataset.title || "",
            description: card.dataset.description || "",
            category: card.dataset.category || "",
            background: card.dataset.background || "",
            image: image?.getAttribute("src") || "",
            alt: image?.alt || "",
            caption: caption?.textContent.trim() || "",
        };
    }

    // Initial hero + remaining category slides.
    const destinations = [
        heroDestination,
        ...cards.map(readCard),
    ];

    // Update a reusable carousel card.
    function setCardContent(card, destination) {
        if (!card || !destination) {
            return;
        }

        card.dataset.title = destination.title;
        card.dataset.description = destination.description;
        card.dataset.category = destination.category;
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

    // Crossfade the hero background.
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

        nextBackground.style.transition = "none";
        nextBackground.style.opacity = "0";
        nextBackground.style.backgroundImage = normalizedBackground;

        void nextBackground.offsetHeight;

        nextBackground.style.transition =
            `opacity ${backgroundDuration}ms ease-in-out`;

        nextBackground.style.opacity = "1";

        const previousBackground = currentBackground;

        currentBackground = nextBackground;
        nextBackground = previousBackground;

        currentBackground.classList.remove("hero-background-next");
        currentBackground.classList.add("hero-background-current");

        nextBackground.classList.remove("hero-background-current");
        nextBackground.classList.add("hero-background-next");

        nextBackground.style.opacity = "0";
    }

    // Update main hero content and CTA.
    function updateHero(destination) {
        if (!destination) {
            return;
        }

        const needsUpdate =
            heroTitle.textContent !== destination.title ||
            heroDescription.textContent !== destination.description;

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

        updateBackground(destination.background);
        updateExploreLink(destination.category);
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

    function resetTrackPosition() {
        track.style.transition = "none";
        track.style.transform = "translateX(0)";

        void track.offsetHeight;
    }

    // Rotate the carousel continuously.
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

        const distance = firstCard.offsetWidth + gap;

        track.style.transition =
            `transform ${animationDuration}ms ease-in-out`;

        track.style.transform = `translateX(-${distance}px)`;

        // Update the hero at the beginning of movement.
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

            rotationIndex =
                (rotationIndex + 1) % destinations.length;

            const outgoingHero = destinations[
                (rotationIndex - 1 + destinations.length) %
                destinations.length
            ];

            resetTrackPosition();

            // Move the outgoing card to the end.
            track.appendChild(firstCard);

            void track.offsetHeight;

            track.style.transition =
                `transform ${animationDuration}ms ease-in-out`;

            // Update the content and category slug of each card.
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

            // The outgoing hero becomes the final card.
            const lastCard = track.lastElementChild;

            if (lastCard) {
                setCardContent(lastCard, outgoingHero);
            }
            updateActiveCard();
            updateIndicators();
            isAnimating = false;
        }
        track.addEventListener(
            "transitionend",
            finishSlide
        );
    }

    // Initialize carousel.
    updateActiveCard();
    updateIndicators();

    // Reveal hero after page load.
    if (document.readyState === "complete") {
        requestAnimationFrame(revealHero);
    } else {
        window.addEventListener(
            "load",
            () => requestAnimationFrame(revealHero),
            { once: true }
        );
    }

    // No rotation needed if there are no additional cards.
    if (cards.length === 0) {
        return;
    }

    // Start automatic rotation.
    window.setInterval(
        rotateCarousel,
        slideDuration
    );
});
