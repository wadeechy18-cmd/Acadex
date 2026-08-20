import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          500: "#3b5bfd",
          600: "#2f47d8",
          700: "#2537ad",
        },
      },
    },
  },
  plugins: [],
};

export default config;
