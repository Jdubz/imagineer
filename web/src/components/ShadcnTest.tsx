import React from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

/**
 * Test component to verify shadcn/ui setup
 * This component demonstrates:
 * - Custom color palette (Coral Pink, Turquoise, Yellow)
 * - Core shadcn components (Button, Card, Input, Label)
 * - Tailwind integration
 */
export default function ShadcnTest() {
  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-foreground mb-2">
            shadcn/ui Test Page
          </h1>
          <p className="text-muted-foreground">
            Verifying the artistic color palette and component integration
          </p>
        </div>

        {/* Button Variants */}
        <Card>
          <CardHeader>
            <CardTitle>Button Variants</CardTitle>
            <CardDescription>
              Testing different button styles with our custom theme
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-4">
            <Button variant="default">Primary (Coral Pink)</Button>
            <Button variant="secondary">Secondary (Turquoise)</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="destructive">Destructive</Button>
            <Button variant="link">Link</Button>
          </CardContent>
        </Card>

        {/* Button Sizes */}
        <Card>
          <CardHeader>
            <CardTitle>Button Sizes</CardTitle>
            <CardDescription>
              Small, default, and large button sizes
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-4">
            <Button size="sm">Small</Button>
            <Button size="default">Default</Button>
            <Button size="lg">Large</Button>
            <Button size="icon">🎨</Button>
          </CardContent>
        </Card>

        {/* Form Example */}
        <Card>
          <CardHeader>
            <CardTitle>Form Components</CardTitle>
            <CardDescription>
              Input and label components with focus states
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="test-input">Test Input</Label>
              <Input
                id="test-input"
                placeholder="Try focusing on this input..."
              />
            </div>
            <Button>Submit</Button>
          </CardContent>
        </Card>

        {/* Color Palette Display */}
        <Card>
          <CardHeader>
            <CardTitle>Color Palette</CardTitle>
            <CardDescription>
              Artistic & Creative theme colors
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <div className="h-20 rounded-lg bg-primary"></div>
                <p className="text-sm font-medium">Primary (Coral Pink)</p>
              </div>
              <div className="space-y-2">
                <div className="h-20 rounded-lg bg-secondary"></div>
                <p className="text-sm font-medium">Secondary (Turquoise)</p>
              </div>
              <div className="space-y-2">
                <div className="h-20 rounded-lg bg-accent"></div>
                <p className="text-sm font-medium">Accent (Sunny Yellow)</p>
              </div>
              <div className="space-y-2">
                <div className="h-20 rounded-lg bg-destructive"></div>
                <p className="text-sm font-medium">Destructive (Soft Red)</p>
              </div>
              <div className="space-y-2">
                <div className="h-20 rounded-lg bg-muted"></div>
                <p className="text-sm font-medium">Muted (Light Gray)</p>
              </div>
              <div className="space-y-2">
                <div className="h-20 rounded-lg border-2 border-border"></div>
                <p className="text-sm font-medium">Border</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Next Steps */}
        <Card className="border-primary">
          <CardHeader>
            <CardTitle className="text-primary">✅ Setup Complete!</CardTitle>
            <CardDescription>
              shadcn/ui is configured with the artistic color palette
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm">
              <strong>Phase 1 Foundation:</strong> Complete ✓
            </p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>Tailwind CSS v3 configured</li>
              <li>shadcn/ui components installed</li>
              <li>Custom color palette applied</li>
              <li>Design tokens defined</li>
              <li>Import aliases configured</li>
            </ul>
            <div className="pt-4">
              <Button variant="default" size="lg">
                Ready for Phase 2: Component Migration
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
