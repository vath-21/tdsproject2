import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import os
from datetime import datetime
import requests
import sys
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Ensure AIPROXY_TOKEN is set in the environment
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")
if not AIPROXY_TOKEN:
    print("Error: AIPROXY_TOKEN environment variable is not set.")
    sys.exit(1)

API_BASE = "https://aiproxy.sanand.workers.dev/openai/v1"

def generate_llm_story(analysis, images):
    """
    Generate a narrative about the data analysis using GPT-4o-mini via direct REST API.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AIPROXY_TOKEN}"
    }

    prompt = f"""
    You received a dataset with {analysis['rows']} rows and {analysis['columns']} columns.
    The dataset includes columns: {', '.join(analysis['column_names'])}.
    
    Based on this dataset, you performed:
    - Outlier Detection
    - Correlation Analysis
    - Clustering
    
    Visualizations:
    - Correlation Heatmap: {images['correlation']}
    - Clustering Visualization: {images['clustering']}

    Please write a data story that includes:
    1. The data received, briefly.
    2. How each analysis was performed.
    3. Key insights from the findings.
    4. Implications and recommendations based on the results.

    Use an engaging narrative tone, suitable for presenting findings in a report.
    """

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a data analyst summarizing analysis results into a report."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000
    }

    try:
        response = requests.post(f"{API_BASE}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"Error with OpenAI API: {e}")
        sys.exit(1)

def create_visualizations(df):
    """
    Generate visualizations for the dataset with larger sizes but low detail.
    """
    os.makedirs('visualizations', exist_ok=True)

    # Generate a correlation heatmap without numerical annotations (only colors) with borders around tiles
    plt.figure(figsize=(10, 10), dpi=100)  # Increased figure size (10x10 inches)
    sns.heatmap(
        df.select_dtypes(include=[np.number]).corr(),
        annot=False,  # Remove numerical annotations
        cmap='coolwarm',  # Color map
        linewidths=0.5,  # Border thickness around tiles
        linecolor='black'  # Border color (black)
    )
    correlation_path = 'visualizations/correlation_heatmap.png'
    plt.title('Correlation Heatmap')
    plt.tight_layout()
    plt.savefig(correlation_path)
    plt.close()

    # Generate a clustering visualization (low detail with larger size)
    numeric_data = df.select_dtypes(include=[np.number]).dropna()
    clustering_path = None
    if numeric_data.shape[1] >= 2:
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(numeric_data)
        kmeans = KMeans(n_clusters=3, random_state=42)
        clusters = kmeans.fit_predict(scaled_data)

        plt.figure(figsize=(10, 10), dpi=100)  # Increased figure size (10x10 inches)
        plt.scatter(scaled_data[:, 0], scaled_data[:, 1], c=clusters, cmap='viridis', s=50)
        plt.title('Clustering Visualization (KMeans)')
        plt.xlabel(numeric_data.columns[0])
        plt.ylabel(numeric_data.columns[1])
        plt.colorbar(label='Cluster')
        clustering_path = 'visualizations/clustering_visualization.png'
        plt.tight_layout()
        plt.savefig(clustering_path)
        plt.close()

    return correlation_path, clustering_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python autolysis2.py <path_to_csv_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        sys.exit(1)

    # Load the dataset
    df = pd.read_csv(file_path)

    # Create visualizations
    correlation_path, clustering_path = create_visualizations(df)

    # Perform analysis
    analysis = {
        'rows': len(df),
        'columns': len(df.columns),
        'column_names': df.columns.tolist(),
        'summary_statistics': df.describe().to_string()
    }

    # Images dictionary for the story
    images = {
        'correlation': correlation_path,
        'clustering': clustering_path if clustering_path else "N/A"
    }

    # Generate the LLM story
    story = generate_llm_story(analysis, images)

    # Generate README content
    readme_content = f"""# Data Analysis Report

**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Story of the Analysis
{story}

## Visualizations
- ![Correlation Heatmap]({correlation_path})
- {f'![Clustering Visualization]({clustering_path})' if clustering_path else 'Clustering visualization not generated.'}

## Notes
- For detailed data and visualizations, please refer to the 'visualizations' directory.
"""

    # Save README
    with open('visualizations/README.md', 'w') as f:
        f.write(readme_content)

    print("Generated files in visualizations/:")
    print("- correlation_heatmap.png")
    if clustering_path:
        print("- clustering_visualization.png")
    print("- README.md")


