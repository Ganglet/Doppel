FROM doppel/base:0.1

WORKDIR /app

COPY preprocess_mimic_demo.py /app/preprocess_mimic_demo.py
COPY generate_manifest.py /app/generate_manifest.py
COPY validate_dataset.py /app/validate_dataset.py
COPY contracts/schemas/dataset.schema.json /app/contracts/schemas/dataset.schema.json

# Raw MIMIC-III demo CSVs are mounted at runtime (via a K8s volume/configmap
# or a data-init step), not baked into the image — see k8s/jobs/preprocessing-job.yaml.

CMD ["sh", "-c", "python preprocess_mimic_demo.py && python generate_manifest.py && python validate_dataset.py"]