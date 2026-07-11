import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";
export const Sheet = DialogPrimitive.Root; export const SheetTrigger = DialogPrimitive.Trigger; export const SheetClose = DialogPrimitive.Close;
export function SheetContent({ side = "right", className, children, ...props }: React.ComponentProps<typeof DialogPrimitive.Content> & { side?: "left" | "right" }) { return <DialogPrimitive.Portal><DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-slate-950/35 backdrop-blur-sm"/><DialogPrimitive.Content className={cn("fixed inset-y-0 z-50 w-[88vw] max-w-md border bg-white p-5 shadow-2xl", side === "right" ? "right-0 border-l" : "left-0 border-r", className)} {...props}>{children}<DialogPrimitive.Close className="absolute right-4 top-4 rounded-md p-1 hover:bg-muted font-bold text-xs">x<span className="sr-only">Close</span></DialogPrimitive.Close></DialogPrimitive.Content></DialogPrimitive.Portal>; }
export const SheetTitle = DialogPrimitive.Title; export const SheetDescription = DialogPrimitive.Description;
