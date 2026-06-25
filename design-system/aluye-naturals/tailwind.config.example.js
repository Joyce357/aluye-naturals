/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#17130F",
        charcoal: "#2A2520",
        bark: "#594A3B",
        kraft: "#B58A55",
        shea: "#D4A85F",
        clay: "#A8563A",
        botanical: "#365C45",
        sage: "#A7B39C",
        bone: "#F6F1E8",
        cream: "#FCFAF6",
        sand: "#E7D8C3",
        error: "#A62C2C",
        success: "#2F6B45",
      },
      fontFamily: {
        display: ["Cormorant Garamond", "Georgia", "serif"],
        sans: ["Inter", "Arial", "sans-serif"],
      },
      maxWidth: {
        page: "90rem",
        reading: "47.5rem",
      },
      borderRadius: {
        brand: "0.25rem",
      },
      transitionDuration: {
        220: "220ms",
        350: "350ms",
      },
      transitionTimingFunction: {
        brand: "cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [],
};
