function colorDistance(first, second) {
    return Math.sqrt(
        (first.r - second.r) ** 2
        + (first.g - second.g) ** 2
        + (first.b - second.b) ** 2
    );
}

function rgbToHex({ r, g, b }) {
    return `#${[r, g, b]
        .map(value => value.toString(16).padStart(2, '0'))
        .join('')}`;
}

function extractFlagColors(flagEmoji) {
    const canvas = document.createElement('canvas');
    canvas.width = 96;
    canvas.height = 72;

    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!context) return [];

    context.font = '56px "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(flagEmoji, canvas.width / 2, canvas.height / 2);

    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    const buckets = new Map();

    for (let index = 0; index < pixels.length; index += 4) {
        const alpha = pixels[index + 3];
        if (alpha < 160) continue;

        const r = Math.round(pixels[index] / 32) * 32;
        const g = Math.round(pixels[index + 1] / 32) * 32;
        const b = Math.round(pixels[index + 2] / 32) * 32;
        const color = {
            r: Math.min(r, 255),
            g: Math.min(g, 255),
            b: Math.min(b, 255),
        };
        const key = `${color.r},${color.g},${color.b}`;
        const bucket = buckets.get(key) || { ...color, count: 0 };
        bucket.count += alpha / 255;
        buckets.set(key, bucket);
    }

    const selected = [];
    const colorsByFrequency = [...buckets.values()]
        .sort((first, second) => second.count - first.count);

    for (const color of colorsByFrequency) {
        if (selected.every(existing => colorDistance(existing, color) >= 72)) {
            selected.push(color);
        }
        if (selected.length === 4) break;
    }

    return selected.map(rgbToHex);
}

document.addEventListener('DOMContentLoaded', function() {
    const paletteCache = new Map();

    function resetLoadingCards() {
        document.querySelectorAll('.flag-border-card.is-loading').forEach(card => {
            card.classList.remove('is-loading');
            card.getAnimations({ subtree: true }).forEach(animation => {
                if (animation.animationName === 'country-border-spin') {
                    animation.updatePlaybackRate(1);
                }
            });
        });
    }

    // Reset before a document enters bfcache and after it is restored from it.
    window.addEventListener('pagehide', resetLoadingCards);
    window.addEventListener('pageshow', resetLoadingCards);

    document.querySelectorAll('.flag-border-card').forEach(card => {
        let colors = paletteCache.get(card.dataset.countrySlug);
        if (!colors) {
            const catalogFlag = typeof flagCatalog === 'undefined'
                ? null
                : flagCatalog.find(flag => flag.name === card.dataset.countrySlug);
            colors = catalogFlag
                ? [catalogFlag.t, catalogFlag.p, catalogFlag.h]
                : extractFlagColors(card.dataset.countryFlag);
            colors = colors.filter(Boolean);
            paletteCache.set(card.dataset.countrySlug, colors);
        }

        if (colors.length < 2) return;

        const gradientColors = [...colors, colors[0]];
        card.style.setProperty('--country-flag-colors', gradientColors.join(', '));
        card.addEventListener('mouseenter', function() {
            const randomAnimationOffset = Math.random() * 6;
            card.style.setProperty('--country-border-delay', `-${randomAnimationOffset}s`);
        });

        card.addEventListener('click', function(event) {
            const usesModifiedClick = event.metaKey || event.ctrlKey || event.shiftKey || event.altKey;
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

            if (event.defaultPrevented || event.button !== 0 || usesModifiedClick || prefersReducedMotion) return;

            card.classList.add('is-loading');

            // This changes the rate at the current animation position. It does
            // not change CSS animation-duration, so the flag colours do not jump.
            const borderAnimation = card.getAnimations({ subtree: true })
                .find(animation => animation.animationName === 'country-border-spin');
            if (borderAnimation) {
                borderAnimation.play();
                borderAnimation.updatePlaybackRate(6);
            }
        });
    });
});
