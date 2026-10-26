import type { ButtonHTMLAttributes } from 'react'

// White on the brand red is 4.3:1, so the resting fill is the darker brand red, which passes AA.
const primaryButtonClass =
  'inline-flex h-9 items-center rounded-full bg-aligo-rojo-oscuro px-5 text-sm font-bold text-aligo-blanco hover:bg-aligo-rojo-medio disabled:cursor-wait disabled:opacity-80'

export function PrimaryButton({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" className={`${primaryButtonClass} ${className}`} {...props} />
}

// Light red text fails contrast on the surface grey, so text actions are white with a red underline.
export const textActionClass =
  'text-sm font-medium underline decoration-aligo-rojo decoration-2 underline-offset-4 hover:decoration-aligo-blanco'

export function TextButton({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" className={`${textActionClass} ${className}`} {...props} />
}
