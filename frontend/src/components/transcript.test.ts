import { parseTranscriptLine } from "@/components/transcript";

const encode = (value: unknown): Uint8Array =>
  new TextEncoder().encode(
    typeof value === "string" ? value : JSON.stringify(value),
  );

describe("parseTranscriptLine", () => {
  it("reads a fan line and an idol line", () => {
    expect(parseTranscriptLine(encode({ speaker: "fan", text: "Hi" }))).toEqual(
      { speaker: "fan", text: "Hi" },
    );
    expect(
      parseTranscriptLine(encode({ speaker: "idol", text: "안녕~" })),
    ).toEqual({ speaker: "idol", text: "안녕~" });
  });

  it("returns null for an unknown speaker or a missing text", () => {
    expect(
      parseTranscriptLine(encode({ speaker: "bot", text: "x" })),
    ).toBeNull();
    expect(parseTranscriptLine(encode({ speaker: "fan" }))).toBeNull();
    expect(parseTranscriptLine(encode({ speaker: "fan", text: 3 }))).toBeNull();
  });

  it("returns null for blank text", () => {
    expect(
      parseTranscriptLine(encode({ speaker: "fan", text: "  " })),
    ).toBeNull();
  });

  it("returns null for broken or non-object data", () => {
    expect(parseTranscriptLine(encode("not json"))).toBeNull();
    expect(parseTranscriptLine(encode("null"))).toBeNull();
    expect(parseTranscriptLine(encode("[1]"))).toBeNull();
  });
});
