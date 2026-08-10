import { z } from "zod";

export const MermaidConfigSchema = z.object({
  enabled: z.boolean().default(true),
  theme: z.enum(["default", "forest", "dark", "neutral", "base"]).default("default"),
  darkTheme: z.enum(["default", "forest", "dark", "neutral", "base"]).default("dark"),
  startOnLoad: z.boolean().default(true),
  securityLevel: z.enum(["strict", "loose", "antiscript", "sandbox"]).default("strict"),
  flowchart: z.object({
    htmlLabels: z.boolean().default(true),
    curve: z.enum(["basis", "linear", "cardinal", "monotoneX", "stepBefore", "stepAfter"]).default("basis"),
    padding: z.number().int().nonnegative().default(15),
    useMaxWidth: z.boolean().default(true),
  }).default({}),
  sequence: z.object({
    showSequenceNumbers: z.boolean().default(false),
    wrap: z.boolean().default(true),
    wrapPadding: z.number().int().nonnegative().default(50),
    actorMargin: z.number().int().nonnegative().default(50),
  }).default({}),
  journey: z.object({
    showActivityLabels: z.boolean().default(true),
  }).default({}),
  gantt: z.object({
    axisFormat: z.string().default("%Y-%m-%d"),
    useMaxWidth: z.boolean().default(true),
  }).default({}),
  classDiagram: z.object({
    arrowMarkerAbsolute: z.boolean().default(false),
  }).default({}),
  stateDiagram: z.object({
    arrowMarkerAbsolute: z.boolean().default(false),
  }).default({}),
  er: z.object({
    useMaxWidth: z.boolean().default(true),
  }).default({}),
  gitGraph: z.object({
    mainBranchName: z.string().default("main"),
    showBranches: z.boolean().default(true),
    showCommitLabel: z.boolean().default(true),
  }).default({}),
  lazyRender: z.boolean().default(true),
  maxCacheSize: z.number().int().nonnegative().default(50),
});

export type MermaidConfig = z.infer<typeof MermaidConfigSchema>;
