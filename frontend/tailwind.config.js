/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0a0f1c",
        panel: "#0f1729",
        panel2: "#131d33",
        edge: "#1e2a45",
        accent: "#e60028", // Apex Bank red
        accent2: "#38bdf8",
        muted: "#8aa0c0",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
