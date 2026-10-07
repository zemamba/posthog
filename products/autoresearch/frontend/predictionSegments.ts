/**
 * Probability cut points between the segments. Both sit on a histogram decile boundary,
 * so every histogram bar belongs to exactly one segment.
 */
export const PREDICTION_SEGMENT_THRESHOLDS = { high: 0.6, low: 0.2 } as const

export type PredictionSegmentKey = 'likely' | 'possible' | 'unlikely'

export interface PredictionSegmentDefinition {
    key: PredictionSegmentKey
    label: string
    range: string
    /** Tailwind background class for the segment's card accent and histogram bars. */
    colorClassName: string
}

const { high, low } = PREDICTION_SEGMENT_THRESHOLDS

export const PREDICTION_SEGMENTS: PredictionSegmentDefinition[] = [
    { key: 'likely', label: 'Likely', range: `${high * 100}% and above`, colorClassName: 'bg-success' },
    { key: 'possible', label: 'Possible', range: `${low * 100}% to ${high * 100}%`, colorClassName: 'bg-warning' },
    { key: 'unlikely', label: 'Unlikely', range: `Below ${low * 100}%`, colorClassName: 'bg-muted' },
]

export function predictionSegmentFor(probability: number): PredictionSegmentDefinition {
    const [likely, possible, unlikely] = PREDICTION_SEGMENTS
    return probability >= high ? likely : probability >= low ? possible : unlikely
}
