const chromePath =
  process.env.CHROME_PATH ||
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

module.exports = {
  ci: {
    collect: {
      startServerCommand:
        ".\\.venv\\Scripts\\python.exe -m waitress --host=127.0.0.1 --port=5000 app:app",
      startServerReadyPattern: "Serving on http://127.0.0.1:5000",
      url: ["http://127.0.0.1:5000/"],
      numberOfRuns: 2,
      settings: {
        chromePath,
        chromeFlags: "--headless --no-sandbox --disable-gpu",
        preset: "desktop",
        onlyCategories: ["performance", "accessibility", "best-practices", "seo"],
      },
    },
    assert: {
      assertions: {
        "categories:performance": ["warn", { minScore: 0.8 }],
        "categories:accessibility": ["error", { minScore: 0.9 }],
        "categories:best-practices": ["error", { minScore: 0.9 }],
        "categories:seo": ["error", { minScore: 0.95 }],
        "largest-contentful-paint": ["warn", { maxNumericValue: 3000 }],
        "cumulative-layout-shift": ["error", { maxNumericValue: 0.1 }],
      },
    },
    upload: {
      target: "filesystem",
      outputDir: "./reports/lighthouse",
    },
  },
};
