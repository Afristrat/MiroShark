import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

/**
 * useScrollFadeIn — reactive helper that flips an `isVisible` ref to `true`
 * the first time `targetRef` enters the viewport. Adds the `ms-anim-fade-in`
 * class (defined globally in components.css) directly on the element so the
 * caller doesn't need to bind the class manually.
 *
 * Behaviour:
 *  - Uses IntersectionObserver (no third-party deps).
 *  - One-shot by default: stops observing once the element has appeared.
 *  - Honours `prefers-reduced-motion: reduce` strictly — if the user opted
 *    out of motion, we treat the element as visible immediately and skip
 *    the observer + animation entirely.
 *  - Safe in SSR / non-browser contexts (IntersectionObserver lookups are
 *    guarded).
 *
 * @param {import('vue').Ref<HTMLElement | HTMLElement[] | null>} targetRef
 *   Either a single template ref or a `ref([])` populated by `:ref` on
 *   `v-for`. Both shapes are handled transparently.
 * @param {{
 *   threshold?: number,
 *   rootMargin?: string,
 *   once?: boolean,
 *   animationClass?: string,
 * }} [options]
 * @returns {{ isVisible: import('vue').Ref<boolean> }}
 */
export function useScrollFadeIn(targetRef, options = {}) {
  const {
    threshold = 0.15,
    rootMargin = '0px',
    once = true,
    animationClass = 'ms-anim-fade-in',
  } = options

  const isVisible = ref(false)

  // Detect reduced-motion + IntersectionObserver availability up-front so we
  // can short-circuit the rest of the composable.
  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const supportsObserver =
    typeof window !== 'undefined' && 'IntersectionObserver' in window

  let observer = null
  // Track the elements we've attached to so we can detach cleanly when the
  // ref shape changes (e.g. cards rendered after async fetch).
  const observed = new WeakSet()

  const collectElements = () => {
    const value = targetRef.value
    if (!value) return []
    if (Array.isArray(value)) {
      return value.filter((el) => el instanceof HTMLElement)
    }
    return value instanceof HTMLElement ? [value] : []
  }

  const markVisible = (el) => {
    if (el && animationClass) el.classList.add(animationClass)
    isVisible.value = true
  }

  const onIntersect = (entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        markVisible(entry.target)
        if (once && observer) {
          observer.unobserve(entry.target)
        }
      }
    }
  }

  const attach = () => {
    const els = collectElements()
    if (els.length === 0) return

    // Reduced-motion path: reveal immediately, no observer, no animation.
    if (prefersReducedMotion || !supportsObserver) {
      for (const el of els) markVisible(el)
      return
    }

    if (!observer) {
      observer = new IntersectionObserver(onIntersect, {
        threshold,
        rootMargin,
      })
    }

    for (const el of els) {
      if (!observed.has(el)) {
        observer.observe(el)
        observed.add(el)
      }
    }
  }

  // Re-attach when the underlying ref changes (e.g. v-for list grows after
  // an async fetch). `flush: 'post'` ensures Vue has actually committed the
  // DOM update before we observe.
  watch(targetRef, attach, { flush: 'post', deep: false })

  onMounted(() => {
    attach()
  })

  onBeforeUnmount(() => {
    if (observer) {
      observer.disconnect()
      observer = null
    }
  })

  return { isVisible }
}
