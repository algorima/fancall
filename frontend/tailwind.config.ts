import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
    "./node_modules/@aioia/core/dist/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
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
