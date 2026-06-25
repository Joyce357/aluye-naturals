const body = document.body;
const menu = document.querySelector("#mobile-menu");
const menuButton = document.querySelector("[data-menu-open]");
const menuClose = document.querySelector("[data-menu-close]");
const toast = document.querySelector("#toast");
const cartCount = document.querySelectorAll("[data-cart-count]");
let cartItems = 0;
let lastTrigger = null;

const currencyOptions = {
  USD: { rate: 1, locale: "en-US" },
  CAD: { rate: 1.36, locale: "en-CA" },
  GBP: { rate: 0.79, locale: "en-GB" },
  NGN: { rate: 1600, locale: "en-NG" },
};

function updateCurrency(root = document) {
  const code = localStorage.getItem("aluye-currency") || "USD";
  const option = currencyOptions[code] || currencyOptions.USD;
  root.querySelectorAll("[data-money][data-price]").forEach((element) => {
    const basePrice = Number(element.dataset.price);
    if (Number.isNaN(basePrice)) return;
    element.textContent = new Intl.NumberFormat(option.locale, {
      style: "currency",
      currency: code,
      minimumFractionDigits: code === "NGN" ? 0 : 0,
      maximumFractionDigits: code === "NGN" ? 0 : 2,
    }).format(basePrice * option.rate);
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

function openPanel(panel, trigger) {
  if (!panel) return;
  lastTrigger = trigger;
  panel.hidden = false;
  body.classList.add("overflow-hidden");
  requestAnimationFrame(() => panel.classList.remove("opacity-0"));
  panel.querySelector("button, input, a")?.focus();
}

function closePanel(panel) {
  if (!panel) return;
  panel.classList.add("opacity-0");
  window.setTimeout(() => {
    panel.hidden = true;
    body.classList.remove("overflow-hidden");
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

document.querySelectorAll("[data-wishlist]").forEach((button) => {
  button.addEventListener("click", () => {
    const active = button.getAttribute("aria-pressed") === "true";
    button.setAttribute("aria-pressed", String(!active));
    button.classList.toggle("text-clay", !active);
  });
});

document.querySelector("#newsletter-form")?.addEventListener("submit", (event) => {
  event.preventDefault();
  const status = document.querySelector("#newsletter-status");
  if (status) status.textContent = "Thank you. Your ritual notes are on their way.";
  event.currentTarget.reset();
});

const quickViewModal = document.querySelector("#quick-view-modal");
const quickViewImage = quickViewModal?.querySelector("[data-quick-view-image]");
const quickViewCategory = quickViewModal?.querySelector("[data-quick-view-category]");
const quickViewTitle = quickViewModal?.querySelector("[data-quick-view-title]");
const quickViewRating = quickViewModal?.querySelector("[data-quick-view-rating]");
const quickViewDescription = quickViewModal?.querySelector("[data-quick-view-description]");
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

quickViewModal?.querySelector("[data-quick-view-close]")?.addEventListener("click", () => {
  quickViewModal.close();
});
quickViewModal?.addEventListener("click", (event) => {
  if (event.target === quickViewModal) quickViewModal.close();
});
quickViewModal?.addEventListener("close", () => quickViewTrigger?.focus());

const collectionControls = document.querySelector("[data-collection-controls]");
if (collectionControls) {
  const grid = document.querySelector("[data-product-grid]");
  const cards = [...document.querySelectorAll("[data-product-card]")];
  const priceFilter = collectionControls.querySelector("[data-price-filter]");
  const tagFilter = collectionControls.querySelector("[data-tag-filter]");
  const sortProducts = collectionControls.querySelector("[data-sort-products]");
  const count = collectionControls.querySelector("[data-product-count]");
  const countSuffix = collectionControls.querySelector("[data-product-count-suffix]");
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
      "price-low": (a, b) => Number(a.dataset.price) - Number(b.dataset.price),
      "price-high": (a, b) => Number(b.dataset.price) - Number(a.dataset.price),
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
  document.querySelector("[data-clear-filters]")?.addEventListener("click", () => {
    priceFilter.value = "all";
    tagFilter.value = "all";
    sortProducts.value = "newest";
    applyCollectionControls();
  });
  applyCollectionControls();
}

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
  dots.forEach((dot, index) => dot.addEventListener("click", () => {
    showSlide(index);
    restart();
  }));
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) restart();
}
