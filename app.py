from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
from openai import OpenAI
from functools import lru_cache
import hashlib
import time

app = Flask(__name__)
CORS(app)  # Allow requests from your WordPress site

# Cache to save API calls and reduce costs
response_cache = {}

def get_deepseek_client():
    """Get DeepSeek API client with error handling"""
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set")
    
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1"
    )

def humanize_text_with_deepseek(ai_text):
    """Your exact humanization logic from Cursor"""
    client = get_deepseek_client()
    
    prompt = f"""
Take AI-style text and rewrite it to sound like a natural college-level human writer while preserving the exact same meaning and information.

TEXT TO HUMANIZE:
{ai_text}

**ZeroGPT Evasion Parameters to Implement:**

**1. Perplexity Management**
- Increase text unpredictability while maintaining coherence
- Introduce grammatical variations (not all perfect)
- Add subtle stylistic inconsistencies
- Mix high and low probability word choices

**2. Burstiness Enhancement**
- Vary sentence lengths dramatically (some very short, some very long)
- Create irregular rhythm in paragraphs
- Use different transition styles between sentences
- Mix simple, compound, and complex sentences unevenly

**3. Repetition Pattern Avoidance**
- Eliminate repeated sentence structures
- Vary transitional phrasing
- Use asymmetric grammatical constructions
- Avoid formulaic openings and closings

**4. Natural "Messiness"**
- Add mild contradictions or qualifications
- Include occasional tangential thoughts
- Vary tone slightly within the text
- Allow minor redundancy where humans would repeat for emphasis

**5. Vocabulary Pattern Management**
- **FORBIDDEN AI-SIGNATURE WORDS (NEVER USE THESE):**
  Furthermore, Moreover, In contrast, Overall, Consequently, Additionally, Thus, Therefore, Hence, Nevertheless, Nonetheless, Notwithstanding, As a result, In conclusion, To summarize, Notably, Importantly, Essentially, Fundamentally, Ultimately, It is important to note, Significant, Demonstrates, In addition

**6. Probability Distribution**
- Include occasional rare or unexpected word choices
- Add slightly awkward but understandable constructions
- Create abrupt but natural stylistic shifts
- Use colloquial expressions occasionally

---

**VOCABULARY REPLACEMENT GUIDE:**

**Transition Words Replacement:**
- "Furthermore" → "Also," "What's more," "On top of that"
- "Moreover" → "Not only that," "Plus," "And another thing"
- "Therefore" → "So," "That's why," "Because of that"
- "Consequently" → "As a result," "Which means," "So then"
- "Additionally" → "Also," "Too," "Another thing"
- "Ever since" → "Since" "When" "Because"

**Formal Phrases to Simplify:**
- "It is important to note" → "Worth mentioning," "Keep in mind," "Remember that"
- "Significant" → "Important," "Major," "Key," "Big"
- "Demonstrates" → "Shows," "Proves," "Points to," "Suggests"
- "In conclusion" → "To wrap up," "So what does this mean?"
- "To summarize" → "Long story short," "Basically," "In short"

**Natural Human Patterns to Inject:**
- Sentence starters: "Well,..." "So,..." "Actually,..." "I mean,..." "You know,..."
- Qualifiers: "Kind of," "Sort of," "A bit," "Pretty much," "More or less"
- Parenthetical asides: "(which is interesting because...)" "(if you think about it)"
- Contractions: it's, don't, can't, won't, that's

**Human Writing Imperfections to Include:**
- Occasional sentence fragments
- Mild run-on sentences
- Starting sentences with "And" or "But"
- Slightly overusing favorite words
- Mixing casual and formal language

**Never Use These Words or Symbols**
- "—" (use "-" instead)
- "Meanwhile" (use "At the same time")
- "flashpoint" (use "critical point")
- "which makes it" (use "so it's" or "making it")

---

**OUTPUT REQUIREMENT:** Return ONLY the humanized text. No explanations.
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "You are a writing coach helping students sound clear, natural, and human. Rewrite text to sound like a college student wrote it."
                },
                {
                    "role": "user",
                    "content": f"""
Here is a piece of text that feels a bit stiff or AI-like:

\"\"\"{ai_text}\"\"\"

Please rewrite it so that:
- it keeps the same ideas and factual content,
- it sounds like a college student wrote it,
- sentence length and structure vary a bit,
- it avoids overly generic or robotic phrasing,
- small imperfections are allowed instead of being perfectly polished.

Return ONLY the rewritten text, with no extra commentary.
"""
                }
            ],
            temperature=0.75,  # Good balance between creativity and consistency
            max_tokens=4000,   # Enough for long texts
        )

        humanized_text = response.choices[0].message.content.strip()
        
        # Post-processing to enforce forbidden items
        humanized_text = re.sub(r'[—–]', '-', humanized_text)
        humanized_text = re.sub(r'\b[Mm]eanwhile\b', 'At the same time', humanized_text)
        humanized_text = re.sub(r'\b[Ff]lashpoint\b', 'critical point', humanized_text)
        humanized_text = re.sub(r'which makes it\b', 'so it\'s', humanized_text)
        
        return humanized_text
        
    except Exception as e:
        print(f"DeepSeek API error: {e}")
        raise

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'AI Humanizer API',
        'version': '1.0.0'
    })

@app.route('/health')
def health():
    """Simple health check"""
    return jsonify({'status': 'healthy'}), 200

@app.route('/humanize', methods=['POST'])
def humanize():
    """Main API endpoint for humanizing text"""
    start_time = time.time()
    
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        ai_text = data.get('text', '').strip()
        
        # Validate input
        if not ai_text:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        # Check text length (limit to 10,000 characters)
        if len(ai_text) > 10000:
            return jsonify({
                'success': False,
                'error': 'Text too long. Maximum 10,000 characters allowed.'
            }), 400
        
        # Create cache key
        cache_key = hashlib.md5(ai_text.encode()).hexdigest()
        
        # Check cache first
        if cache_key in response_cache:
            print(f"Cache hit for key: {cache_key}")
            humanized_text = response_cache[cache_key]
        else:
            # Process through DeepSeek
            print(f"Processing new text (length: {len(ai_text)} chars)")
            humanized_text = humanize_text_with_deepseek(ai_text)
            
            # Cache for 1 hour (3600 seconds)
            response_cache[cache_key] = humanized_text
            # Simple cache cleanup (keep only last 100 items)
            if len(response_cache) > 100:
                # Remove oldest item
                oldest_key = next(iter(response_cache))
                del response_cache[oldest_key]
        
        processing_time = time.time() - start_time
        
        return jsonify({
            'success': True,
            'humanized_text': humanized_text,
            'processing_time': round(processing_time, 2),
            'original_length': len(ai_text),
            'humanized_length': len(humanized_text),
            'cached': cache_key in response_cache
        })
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"Error processing request: {e}")
        
        return jsonify({
            'success': False,
            'error': str(e),
            'processing_time': round(processing_time, 2)
        }), 500

@app.route('/status')
def status():
    """API status with cache info"""
    return jsonify({
        'status': 'operational',
        'cache_size': len(response_cache),
        'service': 'AI Humanizer API'
    })

if __name__ == '__main__':
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    print(f"Starting AI Humanizer API on port {port}...")
    print(f"DeepSeek API key configured: {'Yes' if os.getenv('DEEPSEEK_API_KEY') else 'No'}")
    
    # Note: Use 0.0.0.0 to listen on all interfaces
    app.run(host='0.0.0.0', port=port, debug=False)