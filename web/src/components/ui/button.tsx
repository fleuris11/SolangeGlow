import { Slot } from "@radix-ui/react-slot";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "quiet";
type Size = "md" | "lg";

const variants: Record<Variant, string> = {
  primary: "bg-hibiscus text-sur-hibiscus hover:bg-hibiscus-press",
  secondary: "border-2 border-prune text-prune hover:bg-poudre",
  quiet: "text-prune hover:bg-poudre",
};

const sizes: Record<Size, string> = {
  md: "min-h-12 px-5 text-body gap-2",
  lg: "min-h-14 px-7 text-lead gap-3",
};

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  /** Icon shown before the label. Buttons always carry a word, never an icon alone. */
  icon?: ReactNode;
  fullWidth?: boolean;
  /** Renders the child element (e.g. a Link) with the button styles. */
  asChild?: boolean;
};

export function buttonClasses({
  variant = "primary",
  size = "md",
  fullWidth = false,
  className,
}: Pick<ButtonProps, "variant" | "size" | "fullWidth" | "className">) {
  return cn(
    "inline-flex items-center justify-center rounded-full font-bold transition-colors duration-150 ease-out",
    "disabled:pointer-events-none disabled:opacity-50",
    variants[variant],
    sizes[size],
    fullWidth && "w-full",
    className,
  );
}

export function Button({
  variant,
  size,
  icon,
  fullWidth,
  asChild = false,
  className,
  children,
  type,
  ...props
}: ButtonProps) {
  const Component = asChild ? Slot : "button";
  return (
    <Component
      className={buttonClasses({ variant, size, fullWidth, className })}
      {...(asChild ? {} : { type: type ?? "button" })}
      {...props}
    >
      {asChild ? (
        children
      ) : (
        <>
          {icon && (
            <span aria-hidden className="inline-flex shrink-0">
              {icon}
            </span>
          )}
          {children}
        </>
      )}
    </Component>
  );
}
