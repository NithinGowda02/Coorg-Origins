(() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function initializeHeader() {
        const header = document.querySelector('.site-header');
        if (!header || document.body.classList.contains('admin-page')) return;

        const updateHeader = () => header.classList.toggle('is-scrolled', window.scrollY > 36);
        updateHeader();
        window.addEventListener('scroll', updateHeader, { passive: true });
    }

    function initializeMobileNavigation() {
        const header = document.querySelector('.site-header');
        const toggle = header?.querySelector('.menu-toggle');
        const nav = header?.querySelector('#primary-navigation');
        if (!toggle || !nav) return;

        const setOpen = (open) => {
            header.classList.toggle('menu-open', open);
            toggle.setAttribute('aria-expanded', String(open));
            toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
        };
        toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
        nav.addEventListener('click', (event) => {
            if (event.target.closest('a')) setOpen(false);
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                setOpen(false);
                toggle.focus();
            }
        });
        document.addEventListener('click', (event) => {
            if (!header.contains(event.target)) setOpen(false);
        });
        window.matchMedia('(min-width: 901px)').addEventListener('change', (event) => {
            if (event.matches) setOpen(false);
        });
    }

    function initializeBannerCarousel() {
        const slides = Array.from(document.querySelectorAll('.banner-slide'));
        const dots = Array.from(document.querySelectorAll('.banner-dots button'));
        const arrows = Array.from(document.querySelectorAll('.banner-arrow'));
        if (slides.length < 2) return;

        let activeIndex = 0;
        const showSlide = (index) => {
            activeIndex = index;
            slides.forEach((slide, slideIndex) => slide.classList.toggle('is-active', slideIndex === index));
            dots.forEach((dot, dotIndex) => {
                dot.classList.toggle('is-active', dotIndex === index);
                if (dotIndex === index) dot.setAttribute('aria-current', 'true');
                else dot.removeAttribute('aria-current');
            });
        };

        dots.forEach((dot, index) => dot.addEventListener('click', () => showSlide(index)));
        arrows.forEach((arrow) => arrow.addEventListener('click', () => {
            const direction = Number(arrow.dataset.bannerDirection);
            showSlide((activeIndex + direction + slides.length) % slides.length);
        }));
        if (reducedMotion) return;

        let timer;
        const start = () => {
            window.clearInterval(timer);
            if (!document.hidden) timer = window.setInterval(() => showSlide((activeIndex + 1) % slides.length), 5000);
        };
        const stop = () => window.clearInterval(timer);
        const carousel = document.querySelector('.banner-carousel');
        carousel?.addEventListener('mouseenter', stop);
        carousel?.addEventListener('mouseleave', start);
        carousel?.addEventListener('focusin', stop);
        carousel?.addEventListener('focusout', (event) => {
            if (!carousel.contains(event.relatedTarget)) start();
        });
        document.addEventListener('visibilitychange', start);
        start();
    }

    function initializeSectionReveals() {
        const revealItems = document.querySelectorAll(
            '.story, .featured-section, .category-section, .origin-values, .coming-soon, .product-card, .product-detail, .product-description, .related-section'
        );

        if (reducedMotion || !('IntersectionObserver' in window)) {
            revealItems.forEach((item) => item.classList.add('is-visible'));
            return;
        }

        document.documentElement.classList.add('motion-ready');
        const observer = new IntersectionObserver((entries, currentObserver) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    currentObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

        revealItems.forEach((item) => observer.observe(item));
    }

    function initializeCoffeeAtmosphere() {
        const layer = document.querySelector('.falling-spices');
        if (!layer || reducedMotion) return;

        const isSmallScreen = window.matchMedia('(max-width: 640px)').matches;
        const beanCount = isSmallScreen ? 5 : 8;
        const dewCount = isSmallScreen ? 2 : 4;

        for (let index = 0; index < beanCount; index += 1) {
            const bean = document.createElement('span');
            bean.className = 'falling-spice falling-bean';
            bean.style.setProperty('--spice-left', `${Math.random() * 100}%`);
            bean.style.setProperty('--spice-size', `${12 + Math.random() * 12}px`);
            bean.style.setProperty('--spice-delay', `${Math.random() * -34}s`);
            bean.style.setProperty('--spice-duration', `${27 + Math.random() * 18}s`);
            bean.style.setProperty('--spice-opacity', `${0.08 + Math.random() * 0.11}`);
            bean.style.setProperty('--spice-blur', `${Math.random() < 0.3 ? 1 : 0}px`);
            const rotation = Math.round(Math.random() * 360);
            bean.style.setProperty('--spice-start-rotation', `${rotation}deg`);
            bean.style.setProperty('--spice-mid-rotation', `${rotation + 65}deg`);
            bean.style.setProperty('--spice-end-rotation', `${rotation + 130}deg`);
            bean.style.setProperty('--spice-sway', `${Math.round((Math.random() - 0.5) * 48)}px`);
            bean.style.setProperty('--spice-drift', `${Math.round((Math.random() - 0.5) * 70)}px`);
            layer.appendChild(bean);
        }

        for (let index = 0; index < dewCount; index += 1) {
            const dew = document.createElement('span');
            dew.className = 'falling-spice falling-dew';
            dew.style.setProperty('--spice-left', `${Math.random() * 100}%`);
            dew.style.setProperty('--spice-size', `${2 + Math.random() * 3}px`);
            dew.style.setProperty('--spice-delay', `${Math.random() * -25}s`);
            dew.style.setProperty('--spice-duration', `${22 + Math.random() * 18}s`);
            dew.style.setProperty('--spice-opacity', `${0.16 + Math.random() * 0.12}`);
            dew.style.setProperty('--spice-blur', '0px');
            dew.style.setProperty('--spice-start-rotation', '0deg');
            dew.style.setProperty('--spice-mid-rotation', '0deg');
            dew.style.setProperty('--spice-end-rotation', '0deg');
            dew.style.setProperty('--spice-sway', `${Math.round((Math.random() - 0.5) * 30)}px`);
            dew.style.setProperty('--spice-drift', `${Math.round((Math.random() - 0.5) * 35)}px`);
            layer.appendChild(dew);
        }

        let scrollTimeout;
        window.addEventListener('scroll', () => {
            document.body.classList.add('is-scrolling');
            window.clearTimeout(scrollTimeout);
            scrollTimeout = window.setTimeout(() => document.body.classList.remove('is-scrolling'), 180);
        }, { passive: true });
    }

    function initializeHeroParallax() {
        const hero = document.querySelector('.hero-art');
        if (!hero || reducedMotion || !window.matchMedia('(pointer: fine)').matches) return;

        let frame = 0;
        let scrollFrame = 0;
        const updateScrollParallax = () => {
            if (scrollFrame) return;
            scrollFrame = window.requestAnimationFrame(() => {
                const top = hero.getBoundingClientRect().top;
                const shift = Math.max(-12, Math.min(12, -top * 0.025));
                hero.style.setProperty('--scroll-shift', `${shift.toFixed(1)}px`);
                scrollFrame = 0;
            });
        };
        updateScrollParallax();
        window.addEventListener('scroll', updateScrollParallax, { passive: true });

        hero.addEventListener('pointermove', (event) => {
            if (frame) window.cancelAnimationFrame(frame);
            frame = window.requestAnimationFrame(() => {
                const bounds = hero.getBoundingClientRect();
                const x = ((event.clientX - bounds.left) / bounds.width - 0.5) * -10;
                const y = ((event.clientY - bounds.top) / bounds.height - 0.5) * -8;
                hero.style.setProperty('--parallax-x', `${x.toFixed(1)}px`);
                hero.style.setProperty('--parallax-y', `${y.toFixed(1)}px`);
            });
        });
        hero.addEventListener('pointerleave', () => {
            hero.style.setProperty('--parallax-x', '0px');
            hero.style.setProperty('--parallax-y', '0px');
        });
    }

    initializeHeader();
    initializeMobileNavigation();
    initializeBannerCarousel();
    initializeSectionReveals();
    initializeCoffeeAtmosphere();
    initializeHeroParallax();
})();
