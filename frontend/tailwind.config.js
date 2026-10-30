module.exports = {
  content: ["./src/**/*.{js,jsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        // ── admin / "obsidian" command-center palette
        bg: {
          app: "#050505",
          surface: "#111111",
          surfaceHover: "#1A1A1A",
        },
        accent: {
          orange: "#F97316",
          orangeHover: "#EA580C",
          cyan: "#00F0FF",
          green: "#22C55E",
          red: "#EF4444",
          amber: "#F59E0B",
        },
        ink: {
          primary: "#FAFAFA",
          secondary: "#A1A1AA",
          muted: "#52525B",
        },
        // ── consumer "gatherly" warm-ivory palette
        ivory: {
          50: "#FBF8F2",
          100: "#F5EFE3",
          200: "#EDE3CC",
        },
        emerald: {
          900: "#0B3D2A",
          800: "#0F5132",
          700: "#1A6A45",
          600: "#2A8C5E",
          50: "#E9F2EC",
        },
        gold: {
          600: "#A8842F",
          500: "#B8924A",
          400: "#C8A864",
          200: "#E7D6A6",
        },
        rose: {
          600: "#B83A4B",
        },
        slate: {
          ink: "#0F0F0F",
          mid: "#4A4A4A",
          soft: "#8A8A8A",
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
        serif: ['"Cormorant Garamond"', "Georgia", "serif"],
      },
      borderRadius: {
        sm: "2px",
      },
      boxShadow: {
        glowCyan: "0 0 0 1px rgba(0,240,255,0.5), 0 0 32px -4px rgba(0,240,255,0.5)",
        glowOrange: "0 0 0 1px rgba(249,115,22,0.6), 0 0 32px -4px rgba(249,115,22,0.55)",
        glowGreen: "0 0 0 1px rgba(34,197,94,0.55), 0 0 24px -6px rgba(34,197,94,0.55)",
      },
      keyframes: {
        pulseRing: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(0,240,255,0.4)" },
          "50%": { boxShadow: "0 0 0 10px rgba(0,240,255,0)" },
        },
        flicker: {
          "0%, 100%": { opacity: "1" },
          "47%": { opacity: "1" },
          "50%": { opacity: "0.6" },
          "53%": { opacity: "1" },
        },
        edgeFlow: {
          "0%": { strokeDashoffset: "20" },
          "100%": { strokeDashoffset: "0" },
        },
      },
      animation: {
        pulseRing: "pulseRing 1.8s ease-out infinite",
        flicker: "flicker 4s linear infinite",
        edgeFlow: "edgeFlow 1.2s linear infinite",
      },
    },
  },
  plugins: [],
};
