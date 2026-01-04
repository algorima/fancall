import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import dts from "vite-plugin-dts";
import pkg from "./package.json";

const __dirname = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  build: {
    sourcemap: true,
    lib: {
      entry: {
        index: resolve(__dirname, "src/index.ts"),
        client: resolve(__dirname, "src/client.ts"),
      },
      formats: ["es", "cjs"],
      fileName: (format, entryName) =>
        `${entryName}.${format === "es" ? "js" : "cjs"}`,
    },
    rollupOptions: {
      external: [
        // Automatically externalize peerDependencies
        ...Object.keys(pkg.peerDependencies || {}),
        // Automatically externalize dependencies (install but don't bundle)
        ...Object.keys(pkg.dependencies || {}).filter(
          // Bundle small utilities, externalize others
          (dep) => !["clsx"].includes(dep),
        ),
        // Add peer submodules explicitly
        "react/jsx-runtime",
        /^next\//,
      ],
      output: {
        banner: (chunk) => {
          // Only add 'use client' to client entry point
          if (chunk.name === "client") {
            return '"use client";';
          }
          return "";
        },
      },
    },
  },
  plugins: [
    react(),
    dts({
      include: [
        "src/components/**/*",
        "src/repositories/**/*",
        "src/schemas.ts",
        "src/index.ts",
        "src/client.ts",
        "src/i18n/translations.ts",
      ],
      exclude: [
        "src/app",
        "**/*.test.ts",
        "**/*.test.tsx",
        "**/*.stories.ts",
        "**/*.stories.tsx",
      ],
    }),
  ],
});
