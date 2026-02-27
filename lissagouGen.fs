/*{
    "CREDIT": "Gemini AI",
    "DESCRIPTION": "A generative Lissajous curve machine.",
    "CATEGORIES": [
        "Generative",
        "Visualizer"
    ],
    "INPUTS": [
        {
            "NAME": "freqA",
            "TYPE": "float",
            "DEFAULT": 3.0,
            "MIN": 1.0,
            "MAX": 20.0,
            "LABEL": "Frequency X (a)"
        },
        {
            "NAME": "freqB",
            "TYPE": "float",
            "DEFAULT": 2.0,
            "MIN": 1.0,
            "MAX": 20.0,
            "LABEL": "Frequency Y (b)"
        },
        {
            "NAME": "phase",
            "TYPE": "float",
            "DEFAULT": 0.0,
            "MIN": 0.0,
            "MAX": 6.28,
            "LABEL": "Phase Shift"
        },
        {
            "NAME": "thickness",
            "TYPE": "float",
            "DEFAULT": 0.02,
            "MIN": 0.005,
            "MAX": 0.1,
            "LABEL": "Line Thickness"
        },
        {
            "NAME": "lineColor",
            "TYPE": "color",
            "DEFAULT": [1.0, 1.0, 1.0, 1.0]
        },
        {
            "NAME": "autoAnimate",
            "TYPE": "float",
            "DEFAULT": 1.0,
            "MIN": 0.0,
            "MAX": 5.0,
            "LABEL": "Auto Phase Speed"
        }
    ]
}*/

// Helper function to find the distance from a point to a line segment
float dfLine(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h);
}

void main() {
    // Normalize coordinates to -1.0 to 1.0 (centered)
    vec2 uv = (gl_FragCoord.xy * 2.0 - RENDERSIZE.xy) / min(RENDERSIZE.x, RENDERSIZE.y);
    
    float d = 1e10; // Start with a very large distance
    float animPhase = phase + (TIME * autoAnimate);
    
    // We "draw" the curve by checking segments of the parametric path
    // Increase the loop count for higher quality/smoother lines
    const int segments = 128;
    float stepSize = 6.28318 / float(segments);
    
    vec2 prevP;
    for (int i = 0; i <= segments; i++) {
        float t = float(i) * stepSize;
        
        // The Lissajous formula
        vec2 p = vec2(
            0.8 * sin(freqA * t + animPhase),
            0.8 * sin(freqB * t)
        );
        
        if (i > 0) {
            // Find the distance from the current pixel to this segment of the curve
            d = min(d, dfLine(uv, prevP, p));
        }
        prevP = p;
    }

    // Create the "glow" or "stroke" based on distance and thickness
    float line = smoothstep(thickness, thickness * 0.5, d);
    
    // Add a faint glow/halo
    float glow = exp(-d * 10.0) * 0.3;

    vec4 finalColor = lineColor * (line + glow);
    gl_FragColor = finalColor;
}