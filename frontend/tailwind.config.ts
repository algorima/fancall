import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
    "./node_modules/@aioia/core/dist/**/*.{js,jsx,ts,tsx}",
    "./src/stories/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // Incoming call motion: ripples around the accept button, a slow drift
      // on the caller photo, and content easing in when the call screen opens
      keyframes: {
        ripple: {
          "0%": { transform: "scale(1)", opacity: "0.6" },
          "100%": { transform: "scale(1.9)", opacity: "0" },
        },
        "slow-zoom": {
          "0%": { transform: "scale(1)" },
          "100%": { transform: "scale(1.04)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "fade-up": {
          "0%": { transform: "translateY(16px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        // A heart sent during the call floats up and drifts sideways
        "float-heart": {
          "0%": { transform: "translate(0, 0) scale(0.6)", opacity: "0" },
          "15%": { transform: "translate(0, -1.5rem) scale(1.1)", opacity: "1" },
          "100%": {
            transform: "translate(var(--heart-drift, 0), -13rem) scale(0.9)",
            opacity: "0",
          },
        },
      },
      animation: {
        ripple: "ripple 2s cubic-bezier(0, 0, 0.2, 1) infinite",
        "slow-zoom": "slow-zoom 18s ease-in-out infinite alternate",
        "fade-in": "fade-in 0.6s ease-out both",
        "fade-up": "fade-up 0.5s cubic-bezier(0.2, 0, 0, 1) both",
        "float-heart": "float-heart 1.8s cubic-bezier(0.2, 0, 0, 1) forwards",
      },
      fontSize: {
        // Display - 히어로, 랜딩 페이지 (MD3 기반)
        "display-l": [
          "4.5rem",
          { lineHeight: "1", fontWeight: "700", letterSpacing: "0" },
        ],
        "display-m": [
          "3rem",
          { lineHeight: "1", fontWeight: "700", letterSpacing: "0" },
        ],
        "display-s": [
          "2.25rem",
          { lineHeight: "1.111", fontWeight: "700", letterSpacing: "0" },
        ],
        // Headline - 섹션 제목
        "headline-l": [
          "1.875rem",
          { lineHeight: "1.2", fontWeight: "700", letterSpacing: "0" },
        ],
        "headline-m": [
          "1.5rem",
          { lineHeight: "1.333", fontWeight: "700", letterSpacing: "0" },
        ],
        "headline-s": [
          "1.25rem",
          { lineHeight: "1.4", fontWeight: "700", letterSpacing: "0" },
        ],
        // Title - 본문 내 제목
        "title-l": [
          "1.5rem",
          { lineHeight: "1.333", fontWeight: "500", letterSpacing: "0" },
        ],
        "title-m": [
          "1.25rem",
          { lineHeight: "1.4", fontWeight: "600", letterSpacing: "0" },
        ],
        "title-s": [
          "1.125rem",
          { lineHeight: "1.556", fontWeight: "600", letterSpacing: "0" },
        ],
        // Body - 본문 텍스트
        "body-l": [
          "1.25rem",
          { lineHeight: "1.4", fontWeight: "400", letterSpacing: "0" },
        ],
        "body-m": [
          "1.125rem",
          { lineHeight: "1.556", fontWeight: "400", letterSpacing: "0" },
        ],
        "body-s": [
          "0.875rem",
          { lineHeight: "1.429", fontWeight: "400", letterSpacing: "0.1px" },
        ],
        // Label - 보조 텍스트
        "label-l": [
          "0.875rem",
          { lineHeight: "1.429", fontWeight: "500", letterSpacing: "0" },
        ],
        "label-m": [
          "0.75rem",
          { lineHeight: "1.333", fontWeight: "500", letterSpacing: "0.1px" },
        ],
        "label-s": [
          "0.6875rem",
          { lineHeight: "1.455", fontWeight: "500", letterSpacing: "0.1px" },
        ],
      },
    },
  },
  plugins: [require("@tailwindcss/typography"), require("daisyui")],
  daisyui: {
    themes: [
      {
        light: {
          primary: "#1E9CFD",
          "primary-content": "#FFFFFF",
          secondary: "#88DBFF",
          neutral: "#374151",
          "neutral-content": "#FFFFFF",
          "base-100": "#FFFFFF",
          "base-200": "#F7F7F7",
          "base-300": "#E5E5E5",
          "base-content": "#000000",
          info: "#3ABFF8",
        },
      },
      {
        dark: {
          primary: "#1E9CFD",
          "primary-content": "#FFFFFF",
          secondary: "#88DBFF",
          neutral: "#4B5563",
          "neutral-content": "#FFFFFF",
          "base-100": "#000000",
          "base-200": "#1A1A1A",
          "base-300": "#2D2D2D",
          "base-content": "#FFFFFF",
          info: "#3ABFF8",
        },
      },
    ],
    logs: false,
  },
};

export default config;
