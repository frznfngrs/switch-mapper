import argparse
import os
from .mapper import SwitchMapper

def main():
    parser = argparse.ArgumentParser(description='Map Nexus switch connections and generate diagrams')
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '-o', '--output',
        default='network_diagram',
        help='Output file base name (without extension)'
    )
    args = parser.parse_args()

    # Create mapper instance
    mapper = SwitchMapper(args.config)
    
    # Map network and generate outputs
    diagram_path, text_report = mapper.map_network(args.output)
    
    # Save text report
    report_path = f"{args.output}_report.txt"
    with open(report_path, 'w') as f:
        f.write(text_report)
    
    print(f"\nNetwork mapping complete!")
    if diagram_path and os.path.exists(diagram_path):
        print(f"Diagram saved to: {diagram_path}")
    print(f"Text report saved to: {report_path}")
    
    if not diagram_path:
        print("\nWarning: Failed to generate diagram")

if __name__ == '__main__':
    main()
