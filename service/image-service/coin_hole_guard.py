"""NUC-03: conservative visible-hole veto, not a trained bangle classifier.

Never modifies the YOLO mask or metrology area. A strong hole only changes
automatic acceptance to UNKNOWN, so a person can inspect/correct the shape.
Colour similarity is to the local support, never to a gold-colour standard.
"""
def visible_hole_ratio(image, mask):
    import cv2
    import numpy as np
    binary = (mask > 0).astype(np.uint8)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0.0
    outer = max(contours, key=cv2.contourArea)
    filled = np.zeros_like(binary)
    cv2.drawContours(filled, [outer], -1, 1, cv2.FILLED)
    area = int(filled.sum())
    if area < 400:
        return 0.0
    # First honour an explicit hole in the segmentation mask.
    holes = filled & (1-binary)
    diameter = max(3, int(area**.5 * .08) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(diameter,diameter))
    interior = cv2.erode(filled,kernel)
    # Some segmentation models fill holes. Look for support-like pixels well
    # inside the contour, only when the surrounding support is near-uniform.
    outside = (cv2.dilate(filled,kernel)>0) & (filled==0)
    if outside.sum() >= 40:
        lab = cv2.cvtColor(image,cv2.COLOR_BGR2LAB).astype(np.float32)
        background = lab[outside]
        centre = np.median(background,axis=0)
        distances = np.linalg.norm(background-centre,axis=1)
        if np.percentile(distances,80) <= 12:
            support_like = (np.linalg.norm(lab-centre,axis=2) <= 10).astype(np.uint8)
            holes |= support_like & interior
    holes = cv2.morphologyEx(holes,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(holes,8)
    x,y,w,h = cv2.boundingRect(outer)
    ratios = [0.0]
    for i in range(1,n):
        cx,cy=centroids[i]
        # A large central enclosed region is suspicious; tiny inscriptions,
        # edge glints and small highlights do not trigger this heuristic.
        if (x+w*.22 <= cx <= x+w*.78 and y+h*.22 <= cy <= y+h*.78
                and not np.any((labels==i) & (interior==0))):
            ratios.append(float(stats[i,cv2.CC_STAT_AREA])/area)
    return max(ratios)
