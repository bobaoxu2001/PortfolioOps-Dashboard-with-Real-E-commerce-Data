PYTHON ?= python3

.PHONY: install download build qa dashboard pipeline pipeline-fast clean-processed

install:
	$(PYTHON) -m pip install -r requirements.txt

download:
	$(PYTHON) python/download_olist_data.py

build:
	$(PYTHON) python/build_reporting_layer.py

qa:
	$(PYTHON) python/run_data_contract_tests.py

dashboard:
	$(PYTHON) python/generate_dashboard_assets.py

pipeline:
	$(PYTHON) python/run_pipeline.py

pipeline-fast:
	$(PYTHON) python/run_pipeline.py --skip-download

clean-processed:
	rm -f data/processed/*.csv data/processed/*.duckdb data/processed/*.duckdb.wal
