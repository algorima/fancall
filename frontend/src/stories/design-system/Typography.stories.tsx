import type { Meta, StoryObj } from "@storybook/react";

import { Typography } from "./Typography";

const meta: Meta<typeof Typography> = {
  title: "Design System/03-Typography/Overview",
  component: Typography,
  parameters: {
    chromatic: { disableSnapshot: false },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default typography story showcasing all 15 MD3-based type scales
 */
export const Default: Story = {};
