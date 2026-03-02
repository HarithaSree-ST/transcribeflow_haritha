from transformers import pipeline

# Load pre-trained T5 summarization model
summarizer = pipeline("summarization", model="t5-small")

# Example text
text = """
The increase in global temperatures has led to more frequent and severe weather events, posing a significant threat to ecosystems and human societies. One of the major impacts of climate change is the rise in sea levels, which results from the melting of polar ice caps and glaciers. Coastal areas are particularly vulnerable, as they face higher risks of flooding, storm surges, and erosion. Additionally, the warming atmosphere can hold more moisture, leading to intense and unpredictable precipitation patterns. This variability can cause both severe droughts and devastating floods, affecting agricultural productivity and water resources. 

The effects of climate change are widespread, influencing not only the environment but also the socio-economic stability of communities. For example, changing weather patterns can disrupt food supply chains, increase the prevalence of diseases, and force people to migrate from their homes. To mitigate these effects, countries are investing in adaptive infrastructure, developing early warning systems, and implementing policies to reduce greenhouse gas emissions. 

The collaboration between governments, scientists, and communities is crucial to building resilience against the adverse impacts of climate change. By taking proactive measures, societies can better prepare for the challenges posed by a changing climate and work towards a more sustainable future.
"""

# (Optional but recommended for T5)
text = "summarize: " + text

# Summarize
summary = summarizer(text, max_length=60, min_length=25, do_sample=False)

print("🧠 Summary:", summary[0]['summary_text'])