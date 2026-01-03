import "../src/styles/globals.css";

import type { Preview, Decorator } from "@storybook/react";
import { I18nextProvider } from "react-i18next";
import { withThemeByDataAttribute } from "@storybook/addon-themes";
import { allModes } from "../.storybook/modes";
import { createClientI18nInstance, FANCALL_NS } from "../src/i18n";
import { fancallTranslations } from "../src/i18n/translations";
import { fallbackLng, languages, languageNames } from "../src/i18n/config";
import { MotionGlobalConfig } from "framer-motion";
import isChromatic from "chromatic/isChromatic";

// Disable animations in Chromatic
MotionGlobalConfig.skipAnimations = isChromatic();

const withI18next: Decorator = (Story, context) => {
  const lang = context.globals.locale as string;

  // Create i18n instance with pre-loaded resources for the selected language
  const i18nInstance = createClientI18nInstance(lang, {
    [lang]: {
      [FANCALL_NS]:
        fancallTranslations[lang as keyof typeof fancallTranslations],
    },
  });

  return (
    <I18nextProvider i18n={i18nInstance}>
      <Story {...context} />
    </I18nextProvider>
  );
};

const preview: Preview = {
  globalTypes: {
    locale: {
      name: "Locale",
      description: "Internationalization locale",
      defaultValue: fallbackLng,
      toolbar: {
        icon: "globe",
        items: languages.map((lang) => ({
          value: lang,
          right: lang,
          title: languageNames[lang],
        })),
      },
    },
  },
  parameters: {
    options: {
      storySort: {
        method: "alphabetical",
        order: ["Design System", "*"],
      },
    },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    chromatic: {
      modes: {
        light: allModes["light"],
        dark: allModes["dark"],
      },
    },
  },
  decorators: [
    withI18next,
    withThemeByDataAttribute({
      themes: {
        light: "light",
        dark: "dark",
      },
      defaultTheme: "light",
      attributeName: "data-theme",
    }),
  ],
};

export default preview;
