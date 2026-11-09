import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18211f",
        forest: "#174b3b",
        "forest-dark": "#10382d",
        sand: "#f6f5f0",
        gold: "#b78a45",
      },
      boxShadow: {
        card: "0 16px 48px rgba(24, 33, 31, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
