import os
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
import joblib
from app.ml.predictor import FEATURES, MODEL_PATH

def main():
    rng = np.random.default_rng(42)
    n=2500
    X=np.column_stack([
        rng.uniform(0.5,20,n), rng.uniform(0,4,n), rng.uniform(30,180,n), rng.uniform(5,18,n),
        rng.uniform(0,15,n), rng.uniform(-5,38,n), rng.uniform(20,95,n), rng.uniform(65,100,n)
    ])
    d,p,a,s,w,t,h,soh=X.T
    y=22+13.5*d+10.5*p+0.035*a+1.4*np.maximum(s-8,0)+2.8*w+0.08*np.abs(t-20)+0.015*np.abs(h-50)+0.55*(100-soh)+rng.normal(0,4,n)
    model=GradientBoostingRegressor(random_state=42).fit(X,y)
    os.makedirs(os.path.dirname(MODEL_PATH),exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"saved {MODEL_PATH}; R2={model.score(X,y):.3f}")
if __name__ == "__main__": main()
