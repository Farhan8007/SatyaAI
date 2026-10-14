import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Design tokens for SATYA AI -- light, card-based theme.
        // Base: soft neutral gray page background with solid white cards.
        // Accent: indigo (sidebar + primary actions). Secondary: teal.
        ink: {
          950: "#F4F6FB",
          900: "#FFFFFF",
          800: "#EEF1F8",
          700: "#E3E7F1",
          600: "#CBD2E1",
        },
        ink_text: {
          900: "#1B2233",
          700: "#3D4560",
          500: "#6B7385",
          300: "#98A2B8",
        },
        signal: {
          DEFAULT: "#5B6EE8",
          light: "#7C8CF0",
          dark: "#4453C4",
        },
        intel: {
          DEFAULT: "#18B8A1",
          light: "#3ED9C0",
          dark: "#0F8F7D",
        },
        risk: {
          low: "#18B8A1",
          medium: "#E8A73D",
          high: "#F2793C",
          critical: "#E8465B",
        },
        violet: {
          DEFAULT: "#8B5CF6",
          light: "#A78BFA",
          soft: "#F1EBFE",
        },
        amber: {
          DEFAULT: "#E8A73D",
          light: "#F3C271",
          soft: "#FDF3E3",
        },
        rose: {
          DEFAULT: "#E8465B",
          light: "#F1798A",
          soft: "#FDECEF",
        },
      },
      fontFamily: {
        display: ["var(--font-space-grotesk)", "sans-serif"],
        body: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains)", "monospace"],
      },
      backgroundImage: {
        "grid-glow":
          "radial-gradient(circle at 15% 0%, rgba(91,110,232,0.10), transparent 42%), radial-gradient(circle at 85% 15%, rgba(24,184,161,0.09), transparent 42%), radial-gradient(circle at 50% 100%, rgba(139,92,246,0.06), transparent 45%)",
        "sidebar-gradient": "linear-gradient(160deg, #6C7AE0 0%, #5B6EE8 55%, #4C5CD9 100%)",
        "hero-gradient": "linear-gradient(120deg, #5B6EE8 0%, #7C8CF0 50%, #18B8A1 100%)",
      },
      boxShadow: {
        card: "0 1px 2px rgba(16,24,40,0.04), 0 2px 12px rgba(16,24,40,0.06)",
        "card-lg": "0 8px 30px rgba(16,24,40,0.10)",
        "card-hover": "0 12px 40px rgba(91,110,232,0.16)",
        glow: "0 0 0 4px rgba(91,110,232,0.12)",
      },
      keyframes: {
        floaty: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-8px)" },
        },
      },
      animation: {
        floaty: "floaty 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
