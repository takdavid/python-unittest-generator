python demo-capture.py && sed 's/        CALL/        SKIP CALL/' < capture.log >capture.tmp && mv capture.tmp capture.log && python demo-gen.py && python test_ent.py 
