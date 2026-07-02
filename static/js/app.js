const body = document.body;
const menu = document.querySelector("#mobile-menu");
const menuButton = document.querySelector("[data-menu-open]");
const menuClose = document.querySelector("[data-menu-close]");
const cartCountEls = document.querySelectorAll("[data-cart-count]");
let lastTrigger = null;
const bodyScrollLocks = new Set();

function setBodyScrollLock(key, locked) {
  if (locked) {
    bodyScrollLocks.add(key);
  } else {
    bodyScrollLocks.delete(key);
  }
  body.classList.toggle("overflow-hidden", bodyScrollLocks.size > 0);
}

const currencyOptions = {
  USD: { rate: 1, locale: "en-US" },
  CAD: { rate: 1.36, locale: "en-CA" },
  GBP: { rate: 0.79, locale: "en-GB" },
  NGN: { rate: 1600, locale: "en-NG" },
};

function getCurrency() {
  return localStorage.getItem("aluye-currency") || "USD";
}

function formatMoney(amount, code) {
  code = code || getCurrency();
  const opt = currencyOptions[code] || currencyOptions.USD;
  return new Intl.NumberFormat(opt.locale, {
    style: "currency",
    currency: code,
    minimumFractionDigits: code === "NGN" ? 0 : 0,
    maximumFractionDigits: code === "NGN" ? 0 : 2,
  }).format(amount * opt.rate);
}

function updateCurrency(root = document) {
  const code = getCurrency();
  const option = currencyOptions[code] || currencyOptions.USD;
  root.querySelectorAll("[data-money][data-price]").forEach((element) => {
    const basePrice = Number(element.dataset.price);
    if (Number.isNaN(basePrice)) return;
    element.textContent = formatMoney(basePrice, code);
  });
  root.querySelectorAll("[data-price-option]").forEach((priceOption) => {
    const format = (value) =>
      new Intl.NumberFormat(option.locale, {
        style: "currency",
        currency: code,
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(Number(value) * option.rate);
    const one = format(priceOption.dataset.valueOne);
    const two = priceOption.dataset.valueTwo
      ? format(priceOption.dataset.valueTwo)
      : "";
    if (priceOption.dataset.priceOption === "under") {
      priceOption.textContent = `Under ${one}`;
    } else if (priceOption.dataset.priceOption === "range") {
      priceOption.textContent = `${one}–${two}`;
    } else {
      priceOption.textContent = `${one}+`;
    }
  });
  document.querySelectorAll("[data-currency-selector]").forEach((selector) => {
    selector.value = code;
  });
}

/* ── Panels ── */
function openPanel(panel, trigger) {
  if (!panel) return;
  lastTrigger = trigger;
  panel.hidden = false;
  setBodyScrollLock(panel.id || "panel", true);
  requestAnimationFrame(() => panel.classList.remove("opacity-0"));
  panel.querySelector("button, input, a")?.focus();
}

function closePanel(panel) {
  if (!panel) return;
  panel.classList.add("opacity-0");
  window.setTimeout(() => {
    panel.hidden = true;
    setBodyScrollLock(panel.id || "panel", false);
    lastTrigger?.focus();
  }, 200);
}

menuButton?.addEventListener("click", () => openPanel(menu, menuButton));
menuClose?.addEventListener("click", () => closePanel(menu));
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (menu && !menu.hidden) closePanel(menu);
});

document.querySelectorAll("[data-currency-selector]").forEach((selector) => {
  selector.addEventListener("change", () => {
    localStorage.setItem("aluye-currency", selector.value);
    updateCurrency();
  });
});
updateCurrency();

/* ── Toast ── */
function showToast(message, duration = 2500) {
  const container = document.querySelector("#toast");
  if (!container) return;
  const el = document.createElement("div");
  el.className =
    "pointer-events-auto mb-2 border border-sand bg-white px-5 py-4 text-sm font-semibold shadow-xl transition-opacity duration-300";
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add("opacity-0");
    setTimeout(() => el.remove(), 300);
  }, duration);
}

/* ── Cart count badge ── */
function updateCartCount(count) {
  document.querySelectorAll("[data-cart-count]").forEach((el) => {
    el.textContent = count;
    el.hidden = !count;
  });
}

/* ── Cart Drawer ── */
const cartState = {
  initialized: false,
  open: false,
  drawer: null,
  overlay: null,
  body: null,
  footer: null,
  items: [],
  refreshId: 0,
};

function applyCartState() {
  const { drawer, overlay, open } = cartState;
  if (!drawer || !overlay) return;

  drawer.hidden = false;
  overlay.hidden = false;
  drawer.toggleAttribute("inert", !open);
  drawer.style.transform = open ? "translateX(0)" : "translateX(100%)";
  overlay.style.opacity = open ? "1" : "0";
  overlay.style.pointerEvents = open ? "auto" : "none";
  drawer.setAttribute("aria-hidden", String(!open));
  overlay.setAttribute("aria-hidden", String(!open));

  if (!open) {
    drawer.hidden = true;
    overlay.hidden = true;
  }
  setBodyScrollLock("cart", open);
}

function openCart() {
  if (!cartState.drawer) return;
  if (!cartState.open) {
    cartState.open = true;
    applyCartState();
  }
  refreshCart();
}

function closeCart() {
  if (!cartState.drawer) return;
  cartState.open = false;
  cartState.refreshId += 1;
  applyCartState();
}

function toggleCart() {
  if (!cartState.drawer) return;
  cartState.open ? closeCart() : openCart();
}

function refreshCart() {
  const requestId = ++cartState.refreshId;
  fetch("/api/cart", { headers: { "X-Requested-With": "XMLHttpRequest" } })
    .then((r) => r.json())
    .then((data) => {
      if (requestId === cartState.refreshId) renderCart(data);
    });
}

function renderCart(data) {
  updateCartCount(data.cart_count);
  cartState.items = data.items || [];
  if (!cartState.body) return;
  if (!data.items.length) {
    cartState.body.innerHTML =
      '<p class="py-12 text-center text-bark">Your bag is empty.</p>';
    if (cartState.footer) cartState.footer.hidden = true;
    return;
  }
  const code = getCurrency();
  cartState.body.innerHTML = data.items
    .map(
      (item) => `
    <article class="flex gap-4 border-b border-sand py-4">
      <img src="/media/products/${item.image}" alt="" width="64" height="80" class="h-20 w-16 bg-white object-contain p-1">
      <div class="min-w-0 flex-1">
        <p class="text-sm font-semibold leading-snug">${item.name}</p>
        <p class="mt-1 text-xs text-bark">${item.size}</p>
        <div class="mt-2 flex items-center gap-2">
          <button type="button" data-drawer-qty="${item.slug}" data-delta="-1" class="flex size-7 items-center justify-center border border-sand text-sm font-bold">–</button>
          <span class="w-6 text-center text-sm">${item.quantity}</span>
          <button type="button" data-drawer-qty="${item.slug}" data-delta="1" class="flex size-7 items-center justify-center border border-sand text-sm font-bold">+</button>
        </div>
      </div>
      <div class="flex flex-col items-end gap-2">
        <span class="text-sm font-semibold">${formatMoney(item.line_total, code)}</span>
        <button type="button" data-drawer-remove="${item.slug}" class="text-xs text-bark underline">Remove</button>
      </div>
    </article>`
    )
    .join("");

  if (cartState.footer) {
    cartState.footer.hidden = false;
    const subtotalEl = document.querySelector("#drawer-subtotal");
    const shippingText = document.querySelector("#drawer-shipping-text");
    const shippingBar = document.querySelector("#drawer-shipping-bar");
    if (subtotalEl) subtotalEl.textContent = formatMoney(data.subtotal, code);
    if (data.shipping_remaining > 0) {
      shippingText.textContent = `Add ${formatMoney(data.shipping_remaining, code)} more for free shipping`;
      const pct = Math.min(100, Math.round((data.subtotal / 50) * 100));
      shippingBar.style.width = pct + "%";
    } else {
      shippingText.textContent = "You've unlocked free delivery!";
      shippingBar.style.width = "100%";
    }
  }
}

function cartAction(url, method, bodyStr) {
  fetch(url, {
    method,
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Requested-With": "XMLHttpRequest",
    },
    body: bodyStr || "",
  })
    .then((r) => r.json())
    .then(renderCart);
}

function initCart() {
  if (cartState.initialized) return;
  cartState.initialized = true;

  cartState.drawer = document.querySelector("#cart-drawer");
  cartState.overlay = document.querySelector("#cart-drawer-overlay");
  cartState.body = document.querySelector("#cart-drawer-body");
  cartState.footer = document.querySelector("#cart-drawer-footer");
  if (!cartState.drawer || !cartState.overlay) return;

  applyCartState();

  document.querySelectorAll("[data-cart-trigger]").forEach((btn) => {
    btn.addEventListener("click", toggleCart);
  });

  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-cart-close]")) closeCart();
  });

  cartState.overlay.addEventListener("click", closeCart);

  cartState.body?.addEventListener("click", (e) => {
    const qtyButton = e.target.closest("[data-drawer-qty]");
    if (qtyButton) {
      const slug = qtyButton.dataset.drawerQty;
      const delta = Number(qtyButton.dataset.delta);
      const item = cartState.items.find((i) => i.slug === slug);
      if (!item) return;
      const newQty = Math.max(0, Math.min(10, item.quantity + delta));
      if (newQty === 0) {
        cartAction(`/cart/remove/${slug}`, "POST");
      } else {
        cartAction(`/cart/update/${slug}`, "POST", `quantity=${newQty}`);
      }
      return;
    }

    const removeButton = e.target.closest("[data-drawer-remove]");
    if (removeButton) {
      cartAction(`/cart/remove/${removeButton.dataset.drawerRemove}`, "POST");
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && cartState.open) closeCart();
  });

  window.addEventListener("pagehide", closeCart);
  window.addEventListener("popstate", closeCart);
  window.addEventListener("hashchange", closeCart);
}

if (document.readyState === "complete") {
  initCart();
} else {
  document.addEventListener("DOMContentLoaded", initCart, { once: true });
}

/* ── Quick Add (Feature 1) ── */
document.querySelectorAll("[data-quick-add]").forEach((button) => {
  button.addEventListener("click", (e) => {
    e.preventDefault();
    const url = button.dataset.cartUrl;
    button.textContent = "Adding…";
    button.disabled = true;
    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
      },
      body: "quantity=1",
    })
      .then((r) => r.json())
      .then((data) => {
        updateCartCount(data.cart_count);
        showToast("Added to cart ✓");
        openCart();
        renderCart(data);
      })
      .finally(() => {
        button.textContent = "Quick Add";
        button.disabled = false;
      });
  });
});

/* ── AJAX Add to Cart forms ── */
document.querySelectorAll('form[action*="/cart/add/"]').forEach((form) => {
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    fetch(form.action, {
      method: "POST",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      body: new URLSearchParams(formData),
    })
      .then((r) => r.json())
      .then((data) => {
        updateCartCount(data.cart_count);
        showToast("Added to cart ✓");
        openCart();
        renderCart(data);
      });
  });
});

/* ── Wishlist (localStorage persistence + solid black fill) ── */
const WISHLIST_KEY = "aluye_wishlist";
function getWishlist() {
  try { return JSON.parse(localStorage.getItem(WISHLIST_KEY) || "[]"); } catch(_) { return []; }
}
function saveWishlist(list) { localStorage.setItem(WISHLIST_KEY, JSON.stringify(list)); }
function initWishlistButtons() {
  const wishlist = getWishlist();
  document.querySelectorAll("[data-wishlist]").forEach((button) => {
    const slug = button.dataset.slug || button.closest("[data-product-card]")?.querySelector("a[href*='/products/']")?.href?.split("/products/")[1] || "";
    if (slug && wishlist.includes(slug)) {
      button.setAttribute("aria-pressed", "true");
    }
    button.addEventListener("click", () => {
      const currentSlug = button.dataset.slug || button.closest("[data-product-card]")?.querySelector("a[href*='/products/']")?.href?.split("/products/")[1] || "";
      if (!currentSlug) return;
      const active = button.getAttribute("aria-pressed") === "true";
      button.setAttribute("aria-pressed", String(!active));
      button.classList.add("heart-animate");
      setTimeout(() => button.classList.remove("heart-animate"), 300);
      let wl = getWishlist();
      if (!active) {
        if (!wl.includes(currentSlug)) wl.push(currentSlug);
        showToast("Added to wishlist ✓");
      } else {
        wl = wl.filter(s => s !== currentSlug);
        showToast("Removed from wishlist");
      }
      saveWishlist(wl);
    });
  });
}
initWishlistButtons();

/* ── Header dropdowns (account, wishlist) ── */
function setupDropdown(triggerId, dropdownId) {
  const trigger = document.querySelector("#" + triggerId);
  const dropdown = document.querySelector("#" + dropdownId);
  if (!trigger || !dropdown) return;
  trigger.addEventListener("click", (e) => {
    e.stopPropagation();
    const isOpen = !dropdown.hidden;
    document.querySelectorAll("[id$='-dropdown']").forEach(d => d.hidden = true);
    dropdown.hidden = isOpen;
  });
  dropdown.querySelectorAll("[data-close-dropdown]").forEach(btn => {
    btn.addEventListener("click", () => dropdown.hidden = true);
  });
}
setupDropdown("account-trigger", "account-dropdown");
document.addEventListener("click", () => {
  document.querySelectorAll("#account-dropdown").forEach(d => d.hidden = true);
});

/* ── Newsletter ── */
document
  .querySelector("#newsletter-form")
  ?.addEventListener("submit", (event) => {
    event.preventDefault();
    const status = document.querySelector("#newsletter-status");
    if (status)
      status.textContent =
        "Thank you. Your ritual notes are on their way.";
    event.currentTarget.reset();
  });

/* ── Quick View Modal ── */
const quickViewModal = document.querySelector("#quick-view-modal");
const quickViewImage = quickViewModal?.querySelector("[data-quick-view-image]");
const quickViewCategory = quickViewModal?.querySelector(
  "[data-quick-view-category]"
);
const quickViewTitle = quickViewModal?.querySelector("[data-quick-view-title]");
const quickViewRating = quickViewModal?.querySelector(
  "[data-quick-view-rating]"
);
const quickViewDescription = quickViewModal?.querySelector(
  "[data-quick-view-description]"
);
const quickViewPrice = quickViewModal?.querySelector("[data-quick-view-price]");
const quickViewForm = quickViewModal?.querySelector("[data-quick-view-form]");
const quickViewLink = quickViewModal?.querySelector("[data-quick-view-link]");
let quickViewTrigger = null;

document.querySelectorAll("[data-quick-view]").forEach((button) => {
  button.addEventListener("click", () => {
    if (!quickViewModal) return;
    quickViewTrigger = button;
    quickViewImage.src = button.dataset.image;
    quickViewImage.alt = `${button.dataset.name} product packaging`;
    quickViewCategory.textContent = button.dataset.category;
    quickViewTitle.textContent = button.dataset.name;
    quickViewRating.textContent = `${button.dataset.rating} · ${button.dataset.reviews} reviews`;
    quickViewDescription.textContent = button.dataset.description;
    quickViewPrice.dataset.price = button.dataset.price;
    quickViewForm.action = button.dataset.cartUrl;
    quickViewLink.href = button.dataset.productUrl;
    updateCurrency(quickViewModal);
    quickViewModal.showModal();
    quickViewModal.querySelector("[data-quick-view-close]")?.focus();
  });
});

quickViewModal
  ?.querySelector("[data-quick-view-close]")
  ?.addEventListener("click", () => {
    quickViewModal.close();
  });
quickViewModal?.addEventListener("click", (event) => {
  if (event.target === quickViewModal) quickViewModal.close();
});
quickViewModal?.addEventListener("close", () => quickViewTrigger?.focus());

/* ── Collection Filters ── */
const collectionControls = document.querySelector("[data-collection-controls]");
if (collectionControls) {
  const grid = document.querySelector("[data-product-grid]");
  const cards = [...document.querySelectorAll("[data-product-card]")];
  const priceFilter = collectionControls.querySelector("[data-price-filter]");
  const tagFilter = collectionControls.querySelector("[data-tag-filter]");
  const sortProducts = collectionControls.querySelector("[data-sort-products]");
  const count = collectionControls.querySelector("[data-product-count]");
  const countSuffix = collectionControls.querySelector(
    "[data-product-count-suffix]"
  );
  const emptyState = document.querySelector("[data-filter-empty]");

  const applyCollectionControls = () => {
    const priceRange = priceFilter.value;
    const selectedTag = tagFilter.value;
    let visible = cards.filter((card) => {
      const price = Number(card.dataset.price);
      const tags = card.dataset.badge.split("|");
      const priceMatches =
        priceRange === "all" ||
        (priceRange === "0-25" && price < 25) ||
        (priceRange === "25-50" && price >= 25 && price <= 50) ||
        (priceRange === "50-plus" && price >= 50);
      const tagMatches = selectedTag === "all" || tags.includes(selectedTag);
      card.hidden = !(priceMatches && tagMatches);
      return priceMatches && tagMatches;
    });

    const sorters = {
      newest: (a, b) => Number(b.dataset.index) - Number(a.dataset.index),
      "best-selling": (a, b) =>
        Number(b.dataset.bestSeller) - Number(a.dataset.bestSeller) ||
        Number(b.dataset.reviews) - Number(a.dataset.reviews),
      "price-low": (a, b) =>
        Number(a.dataset.price) - Number(b.dataset.price),
      "price-high": (a, b) =>
        Number(b.dataset.price) - Number(a.dataset.price),
      "top-rated": (a, b) =>
        Number(b.dataset.rating) - Number(a.dataset.rating) ||
        Number(b.dataset.reviews) - Number(a.dataset.reviews),
    };
    visible.sort(sorters[sortProducts.value]);
    visible.forEach((card) => grid.appendChild(card));
    count.textContent = visible.length;
    countSuffix.textContent = visible.length === 1 ? "" : "s";
    emptyState.hidden = visible.length !== 0;
  };

  [priceFilter, tagFilter, sortProducts].forEach((control) => {
    control.addEventListener("change", applyCollectionControls);
  });
  document
    .querySelector("[data-clear-filters]")
    ?.addEventListener("click", () => {
      priceFilter.value = "all";
      tagFilter.value = "all";
      sortProducts.value = "newest";
      applyCollectionControls();
    });
  applyCollectionControls();
}

/* ── Hero Slider ── */
const hero = document.querySelector("[data-hero-slider]");
if (hero) {
  const slides = [...hero.querySelectorAll("[data-hero-slide]")];
  const dots = [...hero.querySelectorAll("[data-hero-dot]")];
  const previous = hero.querySelector("[data-hero-prev]");
  const next = hero.querySelector("[data-hero-next]");
  let active = 0;
  let timer;

  const showSlide = (index) => {
    active = (index + slides.length) % slides.length;
    slides.forEach((slide, slideIndex) => {
      const selected = slideIndex === active;
      const image = slide.querySelector("img[data-src]");
      if (selected && image) {
        image.src = image.dataset.src;
        image.removeAttribute("data-src");
      }
      slide.classList.toggle("opacity-0", !selected);
      slide.classList.toggle("pointer-events-none", !selected);
      slide.setAttribute("aria-hidden", String(!selected));
      slide.toggleAttribute("inert", !selected);
    });
    dots.forEach((dot, dotIndex) => {
      const selected = dotIndex === active;
      dot.classList.toggle("opacity-40", !selected);
      dot.setAttribute("aria-current", selected ? "true" : "false");
    });
  };

  const restart = () => {
    window.clearInterval(timer);
    timer = window.setInterval(() => showSlide(active + 1), 6000);
  };

  previous?.addEventListener("click", () => {
    showSlide(active - 1);
    restart();
  });
  next?.addEventListener("click", () => {
    showSlide(active + 1);
    restart();
  });
  dots.forEach((dot, index) =>
    dot.addEventListener("click", () => {
      showSlide(index);
      restart();
    })
  );
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) restart();
}

/* ── Sticky Add to Cart (Feature 5) ── */
const stickyBarSource = document.querySelector("[data-sticky-source]");
if (stickyBarSource) {
  const stickyBar = document.querySelector("#sticky-add-bar");
  if (stickyBar) {
    const observer = new IntersectionObserver(
      ([entry]) => {
        stickyBar.classList.toggle("translate-y-full", entry.isIntersecting);
        stickyBar.classList.toggle("translate-y-0", !entry.isIntersecting);
      },
      { threshold: 0 }
    );
    observer.observe(stickyBarSource);
  }
}

/* ── Recently Viewed (Feature 6) ── */
function trackRecentlyViewed(slug) {
  const KEY = "aluye-recently-viewed";
  const EXPIRY = 7 * 24 * 60 * 60 * 1000;
  let stored = [];
  try {
    stored = JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch (_) {}
  const now = Date.now();
  stored = stored.filter((e) => now - e.ts < EXPIRY && e.slug !== slug);
  stored.unshift({ slug, ts: now });
  stored = stored.slice(0, 6);
  localStorage.setItem(KEY, JSON.stringify(stored));
}

function getRecentlyViewed(excludeSlug) {
  const KEY = "aluye-recently-viewed";
  const EXPIRY = 7 * 24 * 60 * 60 * 1000;
  let stored = [];
  try {
    stored = JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch (_) {}
  const now = Date.now();
  return stored
    .filter((e) => now - e.ts < EXPIRY && e.slug !== excludeSlug)
    .slice(0, 6);
}

/* ── Live Viewer Counter (Feature 11) ── */
const viewerEl = document.querySelector("[data-live-viewers]");
if (viewerEl) {
  let count = Math.floor(Math.random() * 10) + 3;
  viewerEl.textContent = count;
  setInterval(() => {
    const delta = Math.random() < 0.5 ? -1 : 1;
    count = Math.max(2, Math.min(14, count + delta));
    viewerEl.textContent = count;
  }, 20000 + Math.random() * 20000);
}

/* ── Exit Intent Popup (Feature 14) ── */
const exitPopup = document.querySelector("#exit-popup");
if (exitPopup && !sessionStorage.getItem("aluye-exit-shown") && !localStorage.getItem("aluye-subscribed")) {
  document.addEventListener("mouseleave", (e) => {
    if (e.clientY > 10) return;
    if (sessionStorage.getItem("aluye-exit-shown")) return;
    sessionStorage.setItem("aluye-exit-shown", "1");
    exitPopup.hidden = false;
    requestAnimationFrame(() => exitPopup.classList.remove("opacity-0"));
  });
  exitPopup.querySelector("[data-exit-close]")?.addEventListener("click", () => {
    exitPopup.classList.add("opacity-0");
    setTimeout(() => (exitPopup.hidden = true), 300);
  });
  exitPopup.querySelector("[data-exit-overlay]")?.addEventListener("click", () => {
    exitPopup.classList.add("opacity-0");
    setTimeout(() => (exitPopup.hidden = true), 300);
  });
  exitPopup.querySelector("#exit-form")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const email = exitPopup.querySelector("#exit-email")?.value;
    if (!email) return;
    fetch("/api/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest" },
      body: `email=${encodeURIComponent(email)}`,
    }).then(() => {
      localStorage.setItem("aluye-subscribed", "1");
      exitPopup.querySelector("#exit-form").innerHTML =
        '<p class="py-4 text-center font-semibold text-success">Your 10% code is on its way ✓</p>';
      setTimeout(() => {
        exitPopup.classList.add("opacity-0");
        setTimeout(() => (exitPopup.hidden = true), 300);
      }, 2500);
    });
  });
}

/* ── Search Autocomplete (Feature 20) ── */
const searchInput = document.querySelector("#header-search");
const searchDropdown = document.querySelector("#search-dropdown");
let searchDebounce = null;

if (searchInput && searchDropdown) {
  searchInput.addEventListener("input", () => {
    clearTimeout(searchDebounce);
    const q = searchInput.value.trim();
    if (q.length < 2) {
      searchDropdown.hidden = true;
      return;
    }
    searchDebounce = setTimeout(() => {
      fetch(`/api/search?q=${encodeURIComponent(q)}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((r) => r.json())
        .then((data) => {
          if (!data.results.length) {
            searchDropdown.innerHTML = `<div class="p-4 text-sm text-bark">No products found for "${q}"<br><a href="/shop" class="mt-2 inline-block font-semibold underline">Browse all products</a></div>`;
          } else {
            const code = getCurrency();
            searchDropdown.innerHTML = data.results
              .slice(0, 6)
              .map(
                (r) => `
              <a href="/products/${r.slug}" class="flex items-center gap-3 px-4 py-3 hover:bg-cream">
                <img src="/media/products/${r.image}" alt="" class="size-10 object-contain">
                <div class="min-w-0 flex-1">
                  <p class="text-sm font-semibold">${r.name}</p>
                  <p class="text-xs text-bark">${r.category}</p>
                </div>
                <span class="text-sm font-semibold">${formatMoney(r.price, code)}</span>
              </a>`
              )
              .join("");
            searchDropdown.innerHTML += `<a href="/shop?q=${encodeURIComponent(q)}" class="block border-t border-sand px-4 py-3 text-sm font-semibold hover:bg-cream">See all results for "${q}"</a>`;
          }
          searchDropdown.hidden = false;
        });
    }, 300);
  });
  searchInput.addEventListener("blur", () => {
    setTimeout(() => (searchDropdown.hidden = true), 200);
  });
  searchInput.addEventListener("focus", () => {
    if (searchInput.value.trim().length >= 2 && searchDropdown.innerHTML) {
      searchDropdown.hidden = false;
    }
  });
}

/* ── WhatsApp Chat Bubble (Feature 26) ── */
const waBubble = document.querySelector("#wa-chat-bubble");
if (waBubble) {
  setTimeout(() => {
    waBubble.hidden = false;
    requestAnimationFrame(() => waBubble.classList.remove("opacity-0"));
    setTimeout(() => {
      waBubble.classList.add("opacity-0");
      setTimeout(() => (waBubble.hidden = true), 300);
    }, 6000);
  }, 5000);
  waBubble.querySelector("[data-wa-dismiss]")?.addEventListener("click", (e) => {
    e.stopPropagation();
    waBubble.classList.add("opacity-0");
    setTimeout(() => (waBubble.hidden = true), 300);
  });
}

/* ── Mobile Bottom Nav (Feature 27) ── */
const mobileSearch = document.querySelector("#mobile-search-overlay");
document.querySelector("[data-mobile-search-open]")?.addEventListener("click", () => {
  if (!mobileSearch) return;
  mobileSearch.hidden = false;
  setBodyScrollLock("mobile-search", true);
  requestAnimationFrame(() => mobileSearch.classList.remove("opacity-0"));
  mobileSearch.querySelector("input")?.focus();
});
document.querySelector("[data-mobile-search-close]")?.addEventListener("click", () => {
  if (!mobileSearch) return;
  mobileSearch.classList.add("opacity-0");
  setTimeout(() => {
    mobileSearch.hidden = true;
    setBodyScrollLock("mobile-search", false);
  }, 200);
});

/* ── Buy Now Pay Later tooltip (Feature 8) ── */
document.querySelector("[data-bnpl-info]")?.addEventListener("click", () => {
  const tip = document.querySelector("#bnpl-tooltip");
  if (tip) tip.hidden = !tip.hidden;
});

/* ── Gift Wrapping (Feature 30) ── */
document.querySelector("#gift-wrap-toggle")?.addEventListener("change", (e) => {
  const details = document.querySelector("#gift-wrap-details");
  if (details) {
    details.hidden = !e.target.checked;
    details.style.maxHeight = e.target.checked ? details.scrollHeight + "px" : "0";
  }
});
