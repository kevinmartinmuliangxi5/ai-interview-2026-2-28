import { findActiveSegmentIndex, type TranscriptSegmentLite } from "@/hooks/useTranscriptHighlight";

const SEGMENTS: TranscriptSegmentLite[] = [
  { text: "第一句", start: 0, end: 1.2 },
  { text: "第二句", start: 1.3, end: 2.6 },
  { text: "第三句", start: 2.7, end: 4.0 },
];

describe("findActiveSegmentIndex", () => {
  it("returns -1 for empty transcript segments", () => {
    expect(findActiveSegmentIndex(1.5, [], 0.5)).toBe(-1);
  });

  it("matches segment with ±0.5 second tolerance", () => {
    expect(findActiveSegmentIndex(0.8, SEGMENTS, 0.5)).toBe(0);
    expect(findActiveSegmentIndex(1.25, SEGMENTS, 0.5)).toBe(0);
    expect(findActiveSegmentIndex(2.9, SEGMENTS, 0.5)).toBe(2);
  });

  it("returns -1 when outside all ranges", () => {
    expect(findActiveSegmentIndex(9.0, SEGMENTS, 0.5)).toBe(-1);
  });
});
