import { useCallback, useRef, useState } from 'react'
import { Camera, Trash2, Upload } from 'lucide-react'
import {
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/components/ui/form'
import { Button } from '@/components/ui/button'
import type { Control, FieldPath, FieldValues } from 'react-hook-form'

export interface FormPhotoUploadProps<
    TFieldValues extends FieldValues = FieldValues,
    TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
> {
    control: Control<TFieldValues>
    name: TName
    label: string
    description?: string
    disabled?: boolean
    className?: string
    /** Max file size in bytes (default: 512KB) */
    maxSize?: number
    /** Min dimension in pixels for resize (default: 256) */
    targetSize?: number
}

/**
 * Photo upload form field with:
 * - File picker for image/*
 * - Live preview thumbnail
 * - Client-side resize via Canvas
 * - Base64 output for LDAP jpegPhoto storage
 * - Remove button
 */
export function FormPhotoUpload<
    TFieldValues extends FieldValues = FieldValues,
    TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
>({
    control,
    name,
    label,
    description,
    disabled,
    className,
    maxSize = 512 * 1024,
    targetSize = 256,
}: FormPhotoUploadProps<TFieldValues, TName>) {
    const fileInputRef = useRef<HTMLInputElement>(null)
    const [previewUrl, setPreviewUrl] = useState<string | null>(null)

    const resizeAndConvert = useCallback(
        (file: File): Promise<string> => {
            return new Promise((resolve, reject) => {
                const img = new Image()
                const reader = new FileReader()

                reader.onload = () => {
                    img.onload = () => {
                        const canvas = document.createElement('canvas')
                        // Calculate dimensions maintaining aspect ratio
                        let { width, height } = img
                        const maxDim = Math.max(width, height)
                        if (maxDim > targetSize) {
                            const ratio = targetSize / maxDim
                            width = Math.round(width * ratio)
                            height = Math.round(height * ratio)
                        }
                        canvas.width = width
                        canvas.height = height
                        const ctx = canvas.getContext('2d')
                        if (!ctx) {
                            reject(new Error('Canvas context unavailable'))
                            return
                        }
                        ctx.drawImage(img, 0, 0, width, height)
                        // Convert to JPEG base64
                        const dataUrl = canvas.toDataURL('image/jpeg', 0.85)
                        const base64 = dataUrl.split(',')[1]
                        resolve(base64)
                    }
                    img.onerror = () => reject(new Error('Failed to load image'))
                    img.src = reader.result as string
                }
                reader.onerror = () => reject(new Error('Failed to read file'))
                reader.readAsDataURL(file)
            })
        },
        [targetSize]
    )

    return (
        <FormField
            control={control}
            name={name}
            render={({ field }) => {
                // Build preview URL from field value (base64) or live preview
                const displayUrl =
                    previewUrl ??
                    (field.value ? `data:image/jpeg;base64,${field.value}` : null)

                return (
                    <FormItem className={className}>
                        <FormLabel>{label}</FormLabel>
                        <FormControl>
                            <div className="flex items-center gap-4">
                                {/* Thumbnail preview */}
                                <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-lg border bg-muted">
                                    {displayUrl ? (
                                        <img
                                            src={displayUrl}
                                            alt="Photo preview"
                                            className="h-full w-full object-cover"
                                        />
                                    ) : (
                                        <div className="flex h-full w-full items-center justify-center">
                                            <Camera className="h-8 w-8 text-muted-foreground" />
                                        </div>
                                    )}
                                </div>

                                {/* Actions */}
                                <div className="flex flex-col gap-2">
                                    <input
                                        ref={fileInputRef}
                                        type="file"
                                        accept="image/*"
                                        className="hidden"
                                        disabled={disabled}
                                        onChange={async (e) => {
                                            const file = e.target.files?.[0]
                                            if (!file) return
                                            if (file.size > maxSize * 4) {
                                                // Allow 4x raw size since we'll resize
                                                return
                                            }
                                            try {
                                                const base64 = await resizeAndConvert(file)
                                                field.onChange(base64)
                                                setPreviewUrl(`data:image/jpeg;base64,${base64}`)
                                            } catch {
                                                // silently fail
                                            }
                                            // Reset input so same file can be re-selected
                                            e.target.value = ''
                                        }}
                                    />
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        disabled={disabled}
                                        onClick={() => fileInputRef.current?.click()}
                                    >
                                        <Upload className="mr-2 h-3.5 w-3.5" />
                                        {field.value ? 'Change' : 'Upload'}
                                    </Button>
                                    {field.value && (
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            disabled={disabled}
                                            onClick={() => {
                                                field.onChange('')
                                                setPreviewUrl(null)
                                            }}
                                        >
                                            <Trash2 className="mr-2 h-3.5 w-3.5" />
                                            Remove
                                        </Button>
                                    )}
                                </div>
                            </div>
                        </FormControl>
                        {description && <FormDescription>{description}</FormDescription>}
                        <FormMessage />
                    </FormItem>
                )
            }}
        />
    )
}
