"use client";

import dynamic from "next/dynamic";

// Split from the first load of their pages (ADR-004): a server page cannot do it alone.
export const LazyCreateFlow = dynamic(() => import("./create-flow").then((m) => m.CreateFlow));
export const LazyComments = dynamic(() => import("./comments").then((m) => m.Comments));
