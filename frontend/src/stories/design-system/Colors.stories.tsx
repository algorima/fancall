import type { Meta, StoryObj } from "@storybook/react";

import { Colors } from "./Colors";

const meta: Meta<typeof Colors> = {
  title: "Design System/02-Colors/Overview",
  component: Colors,
};

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default colors story
 */
export const Default: Story = {
  parameters: {
    backgrounds: { default: "dark" },
  },
};
